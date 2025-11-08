# =======================
# File: ftp_utils.py
# =======================
"""
FTP helpers with retries.
"""
from ftplib import FTP
import time
import logging
from pathlib import Path

def get_current_number_from_ftp(ftp_config, retries=3, wait=1.0):
    host = ftp_config.get("host")
    user = ftp_config.get("user")
    passwd = ftp_config.get("passwd")
    remote_dir = ftp_config.get("remote_dir")
    remote_file = ftp_config.get("remote_file")
    last_exc = None
    for attempt in range(retries):
        try:
            ftp = FTP()
            ftp.connect(host, 21, timeout=10)
            ftp.login(user, passwd)
            if remote_dir:
                ftp.cwd(remote_dir)
            lines = []
            ftp.retrlines(f'RETR {remote_file}', lines.append)
            ftp.quit()
            if lines:
                first = lines[0].strip()
                num = int(first.split('/')[0].lstrip("0") or "0")
                logging.info("Current server number: %d", num)
                return num
            else:
                logging.warning("Remote file empty.")
                return None
        except Exception as e:
            last_exc = e
            logging.warning("FTP get failed (%d/%d): %s", attempt+1, retries, e)
            time.sleep(wait * (attempt+1))
    logging.error("FTP get failed after retries: %s", last_exc)
    return None

def upload_temp_file_to_ftp(ftp_config, local_path: Path, retries=3, wait=1.0):
    host = ftp_config.get("host")
    user = ftp_config.get("user")
    passwd = ftp_config.get("passwd")
    remote_dir = ftp_config.get("remote_dir")
    remote_file = ftp_config.get("remote_file")
    last_exc = None
    for attempt in range(retries):
        try:
            ftp = FTP(host, timeout=10)
            ftp.login(user, passwd)
            if remote_dir:
                ftp.cwd(remote_dir)
            with open(local_path, "rb") as f:
                ftp.storbinary(f"STOR {remote_file}", f)
            ftp.quit()
            logging.info("Uploaded %s to FTP as %s/%s", local_path, remote_dir, remote_file)
            return True
        except Exception as e:
            last_exc = e
            logging.warning("FTP upload failed (%d/%d): %s", attempt+1, retries, e)
            time.sleep(wait * (attempt+1))
    logging.error("FTP upload failed after retries: %s", last_exc)
    raise last_exc