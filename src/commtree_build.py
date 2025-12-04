#!/usr/bin/env python3
"""
the comm tree version that uses mpi to build the database from srts
- ranks organized into complete binary tree
- rank 0 initializes database and words table
- rank 0 (root) is the only rank to touch the db
- rank 0 receives aggregated tables to a queue and inserts them to db
- ranks i > (n-2)//2 are leafs. they process their share of srts to json as before.
- leaf nodes read json and build a row of all vid attributes
- other internal comm nodes receive tables from children into queue, zip together
  a couple at a time, then send to parent, and continue
- aggregated data won't be bag-of-words style, but instead an mxn matrix of m data
  inputs and n attributes that creates a sparse matrix whose dimensions are bounded
  by depth of tree times data per leaf node (m) and zipf's law (n)

Requires: mpi4py (pip install mpi4py)
Run with: mpirun -n 8 python3 commtree_build.py
"""
import sqlite3
import subprocess
import sys
import random
import logging
from pathlib import Path
from contextlib import contextmanager
import os
import json
from collections import Counter, defaultdict
import argparse

parser = argparse.ArgumentParser(description="For limiting file input size for benchmarking")
parser.add_argument("--limit", type=int, help="the number of files you want to take input total")
parser.add_argument("--shuffle", action='store_true', help="do you want to shuffle the selection of input (default=false)")
args = parser.parse_args()

# MPI
try:
    from mpi4py import MPI
except Exception as e:
    print("mpi4py is required to run this script. Install with: pip install mpi4py")
    raise

# BASE paths
BASE_DIR = Path(__file__).resolve().parent  # src/
DATABASE_DIR = BASE_DIR / "database"        # src/database/
PIPELINE_DIR = BASE_DIR / "pipeline"        # src/pipeline/

RAW_DIR = BASE_DIR.parent / "raw"      # subtitle-studytool/raw/
JSON_DIR = BASE_DIR.parent / "json"    # subtitle-studytool/json/
DB_PATH = DATABASE_DIR / "korean_vocab.db"

# MPI setup
comm = MPI.COMM_WORLD
rank = comm.Get_rank()
size = comm.Get_size()


@contextmanager
def pushd(new_dir):
    """temporarily change working dir"""
    prev_dir = Path.cwd()
    os.chdir(new_dir)
    try:
        yield
    finally:
        os.chdir(prev_dir)


def run_script(script_path: str):
    script_path = (BASE_DIR / script_path).resolve()
    script_dir = script_path.parent
    if not script_dir.exists():
        raise FileNotFoundError(f"Script dir not found: {script_dir}")
    logging.info(f"> running {script_path.name} in {script_dir} ...")
    with pushd(script_dir):
        try:
            subprocess.run([sys.executable, script_path.name], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f" X Script {script_path.name} failed with exit code {e.returncode}")
            sys.exit(e.returncode)


def log(msg, *args, **kwargs):
    """Log including rank/size prefix for clarity."""
    prefix = f"[rank {rank}/{size}]"
    logging.info(prefix + " " + str(msg), *args, **kwargs)


def run_command(args: list, cwd: Path = None):
#   logging.info(f"▶️ Running: {' '.join(map(str, args))}")
    try:
        subprocess.run(args, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Command failed with exit code {e.returncode}")
        sys.exit(e.returncode)


def parse_timestamp(ts: str) -> float:
    """Convert HH:MM:SS.micro to seconds (float)."""
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def processes_json(source, level, series, video, json_path, word_lookup):
    total_tokens = 0
    matched_tokens = 0
    unmatched_tokens = 0
    ignored_tokens = 0
    word_freq_counter = Counter()
    ignored_words_log = defaultdict(set)
    unmatched_tokens_log = set()
    video_duration_seconds = 0.0
    IGNORED_POS = {"Punctuation", "Josa", "Foreign", "Suffix", "Determiner",
                   "Conjunction", "Exclamation"}

    with open(json_path, encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]

    for entry in data:
        end_ts = entry.get("end")
        if end_ts:
            end_sec = parse_timestamp(end_ts)
            if end_sec > video_duration_seconds:
                video_duration_seconds = end_sec

        for word, pos_tag in entry.get("filtered", []):
            total_tokens += 1
            if pos_tag in IGNORED_POS:
                ignored_tokens += 1
                ignored_words_log[pos_tag].add(word)
                continue

            wid = word_lookup.get((word, pos_tag))
            if wid:
                matched_tokens += 1
                word_freq_counter[wid] += 1
            else:
                unmatched_tokens += 1
                unmatched_tokens_log.add((word, pos_tag))

    duration_minutes = video_duration_seconds / 60.0

    return {
        "source": source,
        "level": level,
        "series": series,
        "video": video,
        "duration_minutes": duration_minutes,
        "total_tokens": total_tokens,
        "matched_tokens": matched_tokens,
        "freq": dict(word_freq_counter)
    }


def merge_batches(batch1, batch2):
    return {"rows": batch1["rows"] + batch2["rows"]}


def do_leaf(srt_files, start_idx, end_idx, word_lookup):
    parent = (rank - 1) // 2

    for local_i, srt_path in enumerate(srt_files[start_idx:end_idx]):
        global_index = start_idx + local_i
        log(f"\n[{global_index}] Processing SRT: {srt_path}")

        parts = srt_path.relative_to(RAW_DIR).parts
        if len(parts) < 4:
            log(f"invalid srt structure: {srt_path}")
            continue
        source, level, series = parts[0], parts[1], parts[2]
        video = Path(parts[-1]).stem
        video_name = ""
        series_name = ""

        # Convert SRT to JSON
        json_path = JSON_DIR / f"{video}.jsonl"
        run_command([
            sys.executable,
            "pipeline/srt_to_json.py",
            "--build-script",
            "--srt", str(srt_path),
            "--json", str(json_path)
        ])
        if not json_path.exists():
            log(f"X Expected json not found: {json_path}")
            continue

        # Build row and send to parent
        results = processes_json(source, level, series, video, str(json_path), word_lookup)
        comm.send({"rows": [results]}, dest=parent, tag=0)
        log(f"✅ Done processing index {global_index}: {video}")

    # Send DONE signal to parent
    comm.send("DONE", dest=parent, tag=0)


def do_comm():
    parent = (rank - 1) // 2
    left = 2 * rank + 1
    right = 2 * rank + 2
    children = [c for c in (left, right) if c < size]

    queue = []
    done_children = 0
    while done_children < len(children):
        msg = comm.recv(source=MPI.ANY_SOURCE, tag=0)
        if msg == "DONE":
            done_children += 1
            continue

        queue.append(msg)
        while len(queue) >= 2:
            b1 = queue.pop(0)
            b2 = queue.pop(0)
            merged = merge_batches(b1, b2)
            comm.send(merged, dest=parent, tag=0)

    # Flush remaining queue
    while queue:
        merged = queue.pop(0)
        comm.send(merged, dest=parent, tag=0)

    comm.send("DONE", dest=parent, tag=0)


def do_root():
    left = 1
    right = 2
    children = [c for c in (left, right) if c < size]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    queue = []
    done_children = 0
    while done_children < len(children):
        msg = comm.recv(source=MPI.ANY_SOURCE, tag=0)
        if msg == "DONE":
            done_children += 1
            continue

        queue.append(msg)
        while queue:
            batch = queue.pop(0)
            for row in batch["rows"]:
                cursor.execute("""
                    INSERT INTO Videos (source, level, series, video,
                                        total_tokens, matched_tokens, duration_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row["source"], row["level"], row["series"], row["video"],
                      row["total_tokens"], row["matched_tokens"], row["duration_minutes"]))
                video_id = cursor.lastrowid

                for wid, freq in row["freq"].items():
                    cursor.execute("""
                        INSERT INTO WordFrequency (video_id, word_id, frequency)
                        VALUES (?, ?, ?)
                        ON CONFLICT(video_id, word_id)
                        DO UPDATE SET frequency = frequency + excluded.frequency
                    """, (video_id, wid, freq))
            conn.commit()
    conn.close()


def main(srt_files):
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    # Rank 0: init DB and broadcast word_lookup
    if rank == 0:
        run_script("database/init_db.py")
        run_script("database/insert_words.py")
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT word, pos_tag, word_id FROM Words")
        word_lookup = {(w, p): wid for w, p, wid in cursor.fetchall()}
        conn.close()
    else:
        word_lookup = None
    word_lookup = comm.bcast(word_lookup, root=0)

    comm.Barrier()
    log("passed barrier after setup ...")
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    if rank == 0:
        do_root()
    elif rank > (size - 2) // 2:
        # Leaf SRT partitioning
#       srt_files = sorted(RAW_DIR.rglob("*.srt"))
        total = len(srt_files)
        leaf_ranks = [i for i in range(size) if i > (size - 2) // 2]
        num_leaves = len(leaf_ranks)
        log(f"found {total} SRT files in total")
        if total == 0:
            log("no srt files found; exiting")
            return
        per = total // num_leaves
        leaf_index = leaf_ranks.index(rank)
        start = leaf_index * per
        if leaf_index == num_leaves - 1:
            end = total
        else:
            end = start + per
        start = max(0, min(start, total))
        end = max(start, min(end, total))
        do_leaf(srt_files, start, end, word_lookup)
    else:
        do_comm()

    log(" > All done.")


if __name__ == "__main__":
    srt_files = sorted(RAW_DIR.rglob("*.srt"))
    if args.limit> 0 and args.shuffle and args.limit < len(srt_files):
      copy = srt_files[:]
      random.shuffle(copy)
      srt_files = copy[:args.limit]
    elif args.limit > 0 and args.limit < len(srt_files):
      srt_files = srt_files[:args.limit]
    main(srt_files)

