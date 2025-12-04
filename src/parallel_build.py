#!/usr/bin/env python3
"""
Parallel wrapper using MPI to distribute SRT -> JSON -> DB work across N processes.

Behavior:
- Rank 0 runs database init scripts (init_db.py, insert_words.py) once, then barrier.
- All ranks discover the same sorted list of SRT files.
- Each rank computes which slice of that list to handle. The last rank will handle any leftover files.
- Each rank processes assigned files, logging global indices (so an index refers to the same file across runs).
- No .done renaming — processing is index-based and idempotent if files are unchanged.

Requires: mpi4py (pip install mpi4py)
Run with: mpirun -n 4 python parallel_build.py
"""
import sqlite3
import subprocess
import sys
import logging
from pathlib import Path
from contextlib import contextmanager
import os

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
DB_PATH = DATABASE_DIR / "korean_vocab.db"  # src/database/korean_vocab.db

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


def log(msg, *args, **kwargs):
    """Log including rank/size prefix for clarity."""
    prefix = f"[rank {rank}/{size}]"
    logging.info(prefix + " " + str(msg), *args, **kwargs)


def run_script(script_path: str):
    """Run a script (used for init_db.py and insert_words.py) from its containing directory."""
    script_path = (BASE_DIR / script_path).resolve()
    script_dir = script_path.parent
    if not script_dir.exists():
        raise FileNotFoundError(f"Script dir not found: {script_dir}")

    log(f"> running {script_path.name} in {script_dir} ...")
    with pushd(script_dir):
        try:
            subprocess.run([sys.executable, script_path.name], check=True)
        except subprocess.CalledProcessError as e:
            logging.error(f" X Script {script_path.name} failed with exit code {e.returncode}")
            # Abort MPI to stop all processes if setup fails
            comm.Abort(e.returncode)


def run_command(args: list, cwd: Path = None):
    log(f"▶️ Running: {' '.join(map(str, args))}")
    try:
        subprocess.run(args, check=True, cwd=cwd)
    except subprocess.CalledProcessError as e:
        logging.error(f"❌ Command failed with exit code {e.returncode}")
        # Do not attempt to continue on this rank; fail fast
        sys.exit(e.returncode)


def insert_video_and_get_id(conn, source, level, series, video):
    """
    Insert a video row and return its video_id.
    Uses a simple SELECT after INSERT. Assumes (source,level,series,video) uniquely identify a row.
    """
    log(f" - inserting video: src={source}, lvl={level}, series={series}, video={video}")
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO Videos (source, level, series, video, series_name, video_name)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (source, level, series, video, None, None))
    conn.commit()

    cursor.execute("""
        SELECT video_id FROM Videos
        WHERE source = ? AND level = ? AND series = ? AND video = ?
    """, (source, level, series, video))
    row = cursor.fetchone()
    if not row:
        raise RuntimeError("Failed to retrieve just-inserted video_id")
    return row[0]


def process_slice(srt_files, start_idx, end_idx):
    """
    Process the given slice of srt_files, using global indices [start_idx, end_idx).
    Each rank calls this on its assigned slice.
    """
    # Use a DB connection with a timeout to reduce SQLITE_BUSY errors under concurrency
    conn = sqlite3.connect(DB_PATH, timeout=30)
    for local_i, srt_path in enumerate(srt_files[start_idx:end_idx]):
        global_index = start_idx + local_i
        log(f"\n[{global_index}] Processing SRT: {srt_path}")

        # compute relative parts: expected <source>/<level>/<series>/<file>.srt
        try:
            parts = srt_path.relative_to(RAW_DIR).parts
        except Exception as e:
            logging.error(f"Could not compute relative path for {srt_path}: {e}")
            continue

        if len(parts) < 4:
            logging.error(f"Invalid SRT structure (expected >=4 parts): {srt_path}")
            continue

        source = parts[0]
        level = parts[1]
        series = parts[2]
        video = Path(parts[-1]).stem
        log(f"  Fields: source={source}, level={level}, series={series}, video={video}")

        # keep placeholders for series_name/video_name for now
        video_name = ""
        series_name = ""

        # Step 1: Convert srt to jsonl
        json_path = JSON_DIR / f"{video}.jsonl"
        run_command([
            sys.executable,
            "pipeline/srt_to_json.py",
            "--build-script",
            "--srt", str(srt_path),
            "--json", str(json_path)
        ])

        if not json_path.exists():
            logging.error(f"X Expected json not found: {json_path}")
            continue

        # Step 2: Insert video and get ID (use the same connection)
        try:
            video_id = insert_video_and_get_id(conn, source, level, series, video)
        except sqlite3.IntegrityError as e:
            # If there is a uniqueness constraint that failed, try to fetch existing id
            log(f"IntegrityError inserting video: {e}. Attempting to SELECT existing row.")
            cur = conn.cursor()
            cur.execute("""
                SELECT video_id FROM Videos
                WHERE source = ? AND level = ? AND series = ? AND video = ?
            """, (source, level, series, video))
            row = cur.fetchone()
            if row:
                video_id = row[0]
            else:
                logging.error("Couldn't obtain video_id after integrity error; skipping file.")
                continue
        except Exception as e:
            logging.error(f"Error inserting video row: {e}")
            continue

        # Step 3: Insert transcript tokens using external script (this will also update Video metadata)
        run_command([
            sys.executable, "database/process_tokens.py",
            str(json_path),
            "--db", str(DB_PATH),
            "--video-id", str(video_id)
        ])

        log(f"✅ Done processing index {global_index}: {video}")

    conn.close()


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    # Rank 0 performs DB initialization
    if rank == 0:
        log("rank 0 running DB init and word population scripts")
        try:
            run_script("database/init_db.py")
            run_script("database/insert_words.py")
        except Exception as e:
            logging.error(f"Setup failed on rank 0: {e}")
            comm.Abort(1)

    # Ensure all ranks wait until DB init completes
    comm.Barrier()
    log("passed barrier after setup")

    # Prepare JSON dir on all ranks (idempotent)
    JSON_DIR.mkdir(parents=True, exist_ok=True)

    # Build the stable sorted list of SRT files on every rank (same deterministic order)
    srt_files = sorted(RAW_DIR.rglob("*.srt"))
    total = len(srt_files)
    log(f"found {total} SRT files in total")

    if total == 0:
        log("no srt files found; exiting")
        return

    # Partition: equal chunks of size `per` for first (size-1) ranks, last rank handles remainder.
    per = total // size
    start = rank * per
    if rank == size - 1:
        end = total
    else:
        end = start + per

    # Safety clamp
    start = max(0, min(start, total))
    end = max(start, min(end, total))

    log(f"assigned slice start={start}, end={end} (count={end-start})")

    # Process assigned slice
    process_slice(srt_files, start, end)

    log("rank finished its assigned work.")


if __name__ == "__main__":
    main()

