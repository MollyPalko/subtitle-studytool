'''
the comm tree version that uses mpi to build the database from srts 
- ranks organized into complete binary tree
- rank 0 initializes database and words table
- rank 0 (root) is the only rank to touch the db
- rank 0 recieves aggregated tables to a queue and inserts them to db
- ranks i > (n-2)//2 are leafs. they process their share of srts to json as before.
- leaf nodes read json and built a row of all vid attributes
- other int comm nodes recieve tables from children into queue, zip together 
  a couple at a time, then send to parent, and continue 
- aggregated data won't be bag of words style, but instead an mxn matrix of m data
  inputs and n attributes that creates a sparse matrix whos dimensions are bounded
  by depth of tree times data per leaf node (m) and zipf's law (n)
'''
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
DB_PATH = DATABASE_DIR / "korean_vocab.db"  # src/database/korean_vocab.db (or wherever db is)


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
  print(f"Running {script_path.name} in {script_dir}")
  #with pushd(script_dir):
  #  subprocess.run([sys.executable, script_path.name], check=True)
  
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
  logging.info(f"▶️ Running: {' '.join(map(str, args))}")
  try:
    subprocess.run(args, check=True, cwd=cwd)
  except subprocess.CalledProcessError as e:
    logging.error(f"❌ Command failed with exit code {e.returncode}")
    sys.exit(e.returncode)


def do_root():
    left = 1
    right = 2
    children = [c for c in (left, right) if c < size]

    # Open DB
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

        # Process all items in queue
        while queue:
            batch = queue.pop(0)
            for row in batch["rows"]:
                # Insert into Videos table
                cursor.execute("""
                    INSERT INTO Videos (source, level, series, video,
                                        total_tokens, matched_tokens, duration_minutes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (row["source"], row["level"], row["series"], row["video"],
                      row["total_tokens"], row["matched_tokens"], row["duration_minutes"]))
                video_id = cursor.lastrowid

                # Insert word frequencies
                for wid, freq in row["freq"].items():
                    cursor.execute("""
                        INSERT INTO WordFrequency (video_id, word_id, frequency)
                        VALUES (?, ?, ?)
                        ON CONFLICT(video_id, word_id)
                        DO UPDATE SET frequency = frequency + excluded.frequency
                    """, (video_id, wid, freq))
            conn.commit()

    conn.close()


def merge_batches(batch1, batch2):
  return {"rows": batch1["rows"] + batch2["rows"]}

def do_comm():
    parent = (rank - 1) // 2
    left = 2 * rank + 1
    right = 2 * rank + 2
    children = [c for c in (left, right) if c < size]

    queue = []

    done_children = 0
    while done_children < len(children):
        # Receive any message from any child
        msg = comm.recv(source=MPI.ANY_SOURCE, tag=0)
        if msg == "DONE":
            done_children += 1
            continue

        queue.append(msg)

        # While there are at least two items, merge and send up
        while len(queue) >= 2:
            b1 = queue.pop(0)
            b2 = queue.pop(0)
            merged = merge_batches(b1, b2)
            comm.send(merged, dest=parent, tag=0)

    # After all children finished, flush remaining queue
    while queue:
        merged = queue.pop(0)
        comm.send(merged, dest=parent, tag=0)

    # Tell parent we are done
    comm.send("DONE", dest=parent, tag=0)



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
  
  # process entries
  for entry in data:
    # update maximum end time
    end_ts = entry.get("end")
    if end_ts:
      end_sec = parse_timestamp(end_ts)
      if end_sec > video_duration_seconds:
        video_duration_seconds = end_sec
    # tokens
    for word, pos_tag in entry.get("filtered", [])
      total_tokens += 1
      if pos_tag in IGNORED_POS:
        ignored_tokens += 1
        continue
      # search word list for word and pos match
      # lookup in memory, no DB
      wid = word_lookup.get((word, pos_tag))
      if wid:
        matched_tokens += 1
        word_freq_counter[wid] += 1
      else:
        unmatched_tokens += 1
      # if match:
      #  get word id
      #  matched_tokens += 1
      # word_frequency_counter[word_id] += 1
      # else:
      #   unmatched_tokens += 1
  duration_minutes = video_duration_seconds / 60.0
  # build the row of data [source,level,series,video,
  #     total_tokens,matched_tokens,duration_minutes,
  #     (word_id, frequency)... ]
  # return aggregated data row
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


def do_leaf(srt_files, start_idx, end_idx):
  # Step 1: calculate parent's rank
  parent = (size-1)//2

  # Step 2: calculate your portion of srt to process
  # collect stable sorted list of all SRT paths
  srt_files = sorted(RAW_DIR.rglob("*.srt"))
  logging.info(f"found {len(srt_files)} SRT files to process.")
#for index, srt_path in enumerate(srt_files):
  for local_i, srt_path in enumerate(srt_files[start_idx:end_idx]):
    global_index = start_idx + local_i
    logging.info(f"\n[{global_index}]  Processing SRT: {srt_path}")

    #parts = srt_path.parts
    parts = srt_path.relative_to(RAW_DIR).parts
    # expected: <source>/<level>/<series>/<video>.srt
    if len(parts) < 4:
        logging.error(f"invalid srt structure: {srt_path}")
        continue
    source = parts[0]
    level = parts[1]
    series = parts[2]
    video = Path(parts[-1]).stem # remove extension
    logging.info(f"  Fields: source={source}, level={level}, series={series}, video={video}")
    video_name = ""
    series_name = ""

    # update this section later to format readable series/vid name and pull info from online
    if source == "drama":
      video_name = "" #f"{show_name} {episode_file}"
      series_name = ""
    elif source == "youtube":
      video_name = ""
      series_name = ""


    # Step 3: Convert srt to jsonl
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
    

    # Step 4: build row of attributes based on json and send to parent
    results = processes_json(source, level, series, video, 
        str(json_path), word_lookup)
    comm.send({"rows": [results]}, dest=parent, tag=0)
    logging.info(f"✅ Done processing index {index}: {video}")


def main():
  logging.basicConfig(level=logging.INFO, format="%(message)s")
  if rank == 0:
      # step 1: init database
      run_script("database/init_db.py")
      # step 2: insert words
      run_script("database/insert_words.py")
      # step 3: export word list
      conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
      cursor = conn.cursor()
      cursor.execute("SELECT word, pos_tag, word_id FROM Words")
      word_lookup = {(w, p): wid for w, p, wid in cursor.fetchall()}
      conn.close()
  else:
      word_lookup = None
  word_lookup = comm.bcast(word_lookup, root=0)
  # step 4: the real work ...
  comm.Barrier()
  logging.info(" passed barrier after setup ...")
  JSON_DIR.mkdir(parents=True, exist_ok=True)
  if rank == 0:
      do_root()
  elif rank > (size-2)//2:
      # partition equal chunks per leaf node, last rank handles remainders
      srt_files = sorted(RAW_DIR.rglob("*.srt"))
      total = len(srt_files)
      leaf_ranks = [i for i in range(size) if i > (size-2)//2]
      num_leaves = len(leaf_ranks)
      log(f"found {total} SRT files in total")
      if total == 0:
        log("no srt files found; exiting")
        return
      per = total//num_leaves
      start = rank*per
      if rank == size - 1:
        end = total
      else:
        end = start + per
      start = max(0, min(start, total))
      end = max(start, min(end, total))
      do_leaf(srt_files, start, end)
  else:
      do_comm()
  logging.info(" > All done.")


if __name__ == "__main__":
  main()

