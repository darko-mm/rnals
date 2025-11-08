# =======================
# File: main.py
# =======================
"""
Entry point. Loads config, folder list, starts watcher.
"""
from pathlib import Path
import os
import json
import logging
from dotenv import load_dotenv
from watcher import WatchService

load_dotenv('config.env')

# Logging config
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
        logging.StreamHandler()
    ],
)

# Environment
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
FTP_HOST = os.getenv("FTP_HOST")
FTP_USER = os.getenv("FTP_USER")
FTP_PASS = os.getenv("FTP_PASS")
REMOTE_DIR = os.getenv("REMOTE_DIR")
REMOTE_FILE = os.getenv("REMOTE_FILE")

CONFIG_JSON = Path("config.json")


def save_folder_paths(folders):
    with CONFIG_JSON.open("w", encoding="utf-8") as fh:
        json.dump({"folders": folders}, fh, indent=4)
    logging.info("Saved folder paths: %s", folders)


def load_folder_paths():
    if CONFIG_JSON.exists():
        with CONFIG_JSON.open("r", encoding="utf-8") as fh:
            cfg = json.load(fh)
            return cfg.get("folders", [])
    return []


def prompt_and_store_folders():
    print("Enter folders to watch (comma separated):")
    folders_input = input().strip()
    folders = [p.strip() for p in folders_input.split(",") if p.strip()]
    save_folder_paths(folders)
    return folders


def validate_folders(folders):
    invalid = [f for f in folders if not os.path.exists(f)]
    if invalid:
        logging.error("These folders don't exist: %s", invalid)
    return invalid


if __name__ == "__main__":
    folders = load_folder_paths()
    if not folders:
        folders = prompt_and_store_folders()

    invalid = validate_folders(folders)
    if invalid:
        print(f"These folders don't exist: {', '.join(invalid)}")
        raise SystemExit(1)

    svc = WatchService(
        folders_to_watch=folders,
        bot_token=BOT_TOKEN,
        chat_id=CHAT_ID,
        ftp_config=dict(
            host=FTP_HOST, user=FTP_USER, passwd=FTP_PASS,
            remote_dir=REMOTE_DIR, remote_file=REMOTE_FILE
        ),
    )
    svc.start()  # blocking until KeyboardInterrupt
