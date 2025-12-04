'''
the quick and dirty wrapper to subprocess call to each script
- initializes database and tables
- populates words table
- for srt files in /raw/, process them into jsonl
- for jsonl files in /json/ add an entry to the video table
- for jsonl files in /json/ insert words into frequency table
'''
import sqlite3
import subprocess
import random
import sys
import logging
from pathlib import Path
from contextlib import contextmanager
import os
import argparse

parser = argparse.ArgumentParser(description="For limiting file input size for benchmarking")
parser.add_argument("--limit", type=int, help="the number of files you want to take input total")
parser.add_argument("--shuffle", action='store_true', help="do you want to shuffle the selection of input (default=false)")
args = parser.parse_args()

#BASE_DIR = Path(__file__).resolve().parent
#RAW_DIR = BASE_DIR / Path("../raw").resolve()
#DB_PATH = BASE_DIR / "database/korean_vocab.db"
#JSON_DIR = BASE_DIR / Path("../json").resolve()
BASE_DIR = Path(__file__).resolve().parent  # src/

DATABASE_DIR = BASE_DIR / "database"        # src/database/
PIPELINE_DIR = BASE_DIR / "pipeline"        # src/pipeline/

RAW_DIR = BASE_DIR.parent / "raw"      # subtitle-studytool/raw/
JSON_DIR = BASE_DIR.parent / "json"    # subtitle-studytool/json/
DB_PATH = DATABASE_DIR / "korean_vocab.db"  # src/database/korean_vocab.db (or wherever db is)


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
# print(f"Running {script_path.name} in {script_dir}")
  #with pushd(script_dir):
  #  subprocess.run([sys.executable, script_path.name], check=True)
  
# logging.info(f"> running {script_path.name} in {script_dir} ...")
  
  with pushd(script_dir):
    try:
      subprocess.run([sys.executable, script_path.name], check=True)
    except subprocess.CalledProcessError as e:
      logging.error(f" X Script {script_path.name} failed with exit code {e.returncode}")
      sys.exit(e.returncode)

def run_command(args: list, cwd: Path = None):
# logging.info(f"▶️ Running: {' '.join(map(str, args))}")
  try:
    subprocess.run(args, check=True, cwd=cwd)
  except subprocess.CalledProcessError as e:
    logging.error(f"❌ Command failed with exit code {e.returncode}")
    sys.exit(e.returncode)

def insert_video_and_get_id(conn, source, level, series, video):
#   logging.info(f" - inserting video: src={source}, lvl={level}, series={series}, video={video}")

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

    return cursor.fetchone()[0]


def process_all_srts(srt_files):
  conn = sqlite3.connect(DB_PATH)

  # collect stable sorted list of all SRT paths
  #srt_files = sorted(RAW_DIR.rglob("*.srt"))
  logging.info(f"found {len(srt_files)} SRT files to process.")

  for index, srt_path in enumerate(srt_files):
    logging.info(f"\n[{index}]  Processing SRT: {srt_path}")

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
#   logging.info(f"  Fields: source={source}, level={level}, series={series}, video={video}")
    video_name = ""
    series_name = ""

    # update this section later to format readable series/vid name and pull info from online
    if source == "drama":
      video_name = "" #f"{show_name} {episode_file}"
      series_name = ""
    elif source == "youtube":
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
    
    # Step 2: Insert video and get ID
    video_id = insert_video_and_get_id(conn, source, level, series, video)
    # add video_name and series_name to this function later

    # Step 3: Insert transcript
    run_command([
        sys.executable, "database/process_tokens.py",
        str(json_path),
        "--db", str(DB_PATH),
        "--video-id", str(video_id)
    ])

    logging.info(f"✅ Done processing index {index}: {video}")

  conn.close()


def main(srt_files):
  logging.basicConfig(level=logging.INFO, format="%(message)s")
  # step 1: init database
  run_script("database/init_db.py")
  # step 2: insert words
  run_script("database/insert_words.py")
  # step 3: the real work ...
  logging.info(" ~ begin craziness...")
  JSON_DIR.mkdir(parents=True, exist_ok=True)
  process_all_srts(srt_files)
  logging.info(" > All done.")


if __name__ == "__main__":
  srt_files = sorted(RAW_DIR.rglob("*.srt"))
  if args.limit > 0 and args.shuffle and args.limit < len(srt_files):
    copy = srt_files[:]
    random.shuffle(copy)
    srt_files = copy[:args.limit]
  elif args.limit > 0 and args.limit < len(srt_files):
    srt_files = srt_files[:args.limit]
  main(srt_files)

