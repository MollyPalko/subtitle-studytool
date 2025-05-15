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
import sys
import logging
from pathlib import Path
from contextlib import contextmanager
import os

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
  print(f"Running {script_path.name} in {script_dir}")
  with pushd(script_dir):
    subprocess.run([sys.executable, script_path.name], check=True)
  
  logging.info(f"> running {script_path.name} in {script_dir} ...")
  
  with pushd(script_dir):
    try:
      subprocess.run([sys.executable, script_path.name], check=True)
    except subprocess.CalledProcessError as e:
      logging.error(f" X Script {script_path.name} failed with exit code {e.returncode}")
      sys.exit(e.returncode)

def run_command(args: list, cwd: Path = None):
  logging.info(f"▶️ Running: {' '.join(map(str, args))}")
  try:
    subprocess.run(args, check=True, cwd=cwd)
  except subprocess.CalledProcessError as e:
    logging.error(f"❌ Command failed with exit code {e.returncode}")
    sys.exit(e.returncode)


def insert_video_and_get_id(conn, name, category):
  logging.info(f" - inserting video: {name}, {category}")
  cursor = conn.cursor()
  cursor.execute(
        "INSERT INTO Videos (video_name, category) VALUES (?, ?)", (name, category)
  )
  conn.commit()
  cursor.execute(
        "SELECT video_id FROM Videos WHERE video_name = ? AND category = ?", (name, category)
  )
  return cursor.fetchone()[0]


def process_all_srts():
  conn = sqlite3.connect(DB_PATH)
  for srt_path in RAW_DIR.rglob("*.srt"):
    # skip the file if already processed
    if srt_path.with_suffix(".srt.done").exists():
      logging.info(f" >> skipping already processed: {srt_path}")
      continue

    logging.info(f"  Processing SRT: {srt_path}")

    #parts = srt_path.parts
    parts = srt_path.relative_to(RAW_DIR).parts
    category = parts[0]  # this 'drama' or 'youtube'
    show_and_ep = parts[1:]

    if category == "drama":
      show_name = show_and_ep[0]
      episode_file = Path(show_and_ep[1]).stem
      video_name = f"{show_name} {episode_file}"
    else:
      video_name = Path(show_and_ep[0]).stem


    # Step 1: Convert srt to jsonl
    json_path = JSON_DIR / f"{video_name}.jsonl"
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
    video_id = insert_video_and_get_id(conn, video_name, category)

    # Step 3: Insert transcript
    run_command([
        sys.executable, "database/process_tokens.py",
        str(json_path),
        "--db", str(DB_PATH),
        "--video-id", str(video_id)
    ])

    # Step 4: Mark files as done
    srt_done = srt_path.with_suffix(".srt.done")
    srt_path.rename(srt_done)
    json_done = json_path.with_suffix(".jsonl.done")
    json_path.rename(json_done)

    logging.info(f"✅ Done processing: {video_name}")

  conn.close()


def main():
  logging.basicConfig(level=logging.INFO, format="%(message)s")
  # step 1: init database
  run_script("database/init_db.py")
  # step 2: insert words
  run_script("database/insert_words.py")
  # step 3: the real work ...
  logging.info(" ~ begin craziness...")
  JSON_DIR.mkdir(parents=True, exist_ok=True)
  process_all_srts()
  logging.info(" > All done.")


if __name__ == "__main__":
  main()
