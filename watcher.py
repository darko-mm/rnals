# =======================
# File: watcher.py
# =======================
"""
Watcher service: sets up watchdog observers and a thread pool for processing files.
"""
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from concurrent.futures import ThreadPoolExecutor
import time
import logging
from processor import process_file

class ExcelCreatedHandler(FileSystemEventHandler):
    def __init__(self, folder, executor, ftp_config, bot_token, chat_id):
        self.folder = folder
        self.executor = executor
        self.ftp_config = ftp_config
        self.bot_token = bot_token
        self.chat_id = chat_id

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.lower().endswith(".xlsx"):
            logging.info("New xlsx detected: %s", event.src_path)
            # submit for background processing
            self.executor.submit(process_file,
                                 event.src_path,
                                 ftp_config=self.ftp_config,
                                 bot_token=self.bot_token,
                                 chat_id=self.chat_id)

class WatchService:
    def __init__(self, folders_to_watch, bot_token, chat_id, ftp_config, max_workers=4):
        self.folders = folders_to_watch
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.ftp_config = ftp_config
        self.observers = []
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def start(self):
        for folder in self.folders:
            handler = ExcelCreatedHandler(folder, self.executor, self.ftp_config, self.bot_token, self.chat_id)
            obs = Observer()
            obs.schedule(handler, folder, recursive=True)
            obs.start()
            self.observers.append(obs)
            logging.info("Started watching %s", folder)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            for obs in self.observers:
                obs.stop()
            for obs in self.observers:
                obs.join()
            self.executor.shutdown(wait=True)
            logging.info("Shutdown complete.")