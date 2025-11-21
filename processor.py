# =======================
# File: processor.py
# =======================
"""
Processes a single Excel file: read data, validate against FTP, ask Telegram if needed,
save temp_number.txt, upload to FTP, log and notify.
"""
import time
import logging
import openpyxl
from datetime import datetime
from pathlib import Path
from ftp_utils import get_current_number_from_ftp, upload_files_to_ftp
# from telegram_utils import (
#     send_info_message,
#     send_success_message,
#     send_error_message,
#     ask_confirmation_and_wait,
# )

LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def get_log_file():
    now = datetime.now()
    return LOG_DIR / f"log_{now.strftime('%m')}_{now.year}.txt"


def log_data(file_name, radni_nalog, datum):
    with get_log_file().open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} Processed: {file_name}, RN: {radni_nalog}, Date: {datum}\n")


def save_temp_number(radni_nalog, datum, path=Path("temp_number.txt")):
    # --- Format RN (4 znamenke prije /) ---
    try:
        broj_str, godina_str = str(radni_nalog).split("/")
        broj_fmt = f"{int(broj_str):04d}/{godina_str.strip()}"
    except Exception:
        broj_fmt = str(radni_nalog).strip()

    # --- Format date (DD.MM.YYYY.) ---
    datum_str = str(datum).strip().replace(",", ".").replace("-", ".")
    try:
        datum_obj = datetime.strptime(datum_str.rstrip("."), "%d.%m.%Y")
        datum_fmt = datum_obj.strftime("%d.%m.%Y.")
    except Exception:
        # fallback — handle text like "7.11.2025" manually
        parts = datum_str.replace(".", " ").split()
        if len(parts) >= 3:
            day = parts[0].zfill(2)
            month = parts[1].zfill(2)
            year = parts[2].zfill(4)
            datum_fmt = f"{day}.{month}.{year}."
        else:
            datum_fmt = datum_str

    # --- Compose line with exactly 8 spaces ---
    formatted = f"{broj_fmt}{' ' * 8}{datum_fmt}"
    path.write_text(formatted + "\n", encoding="utf-8")


def safe_load_excel(path, attempts=5, wait=1.0):
    last_exc = None
    for i in range(attempts):
        try:
            wb = openpyxl.load_workbook(path, data_only=True)
            return wb
        except PermissionError as e:
            last_exc = e
            logging.warning("File %s locked; retrying (%d/%d)...", path, i + 1, attempts)
            time.sleep(wait * (i + 1))
        except Exception as e:
            last_exc = e
            logging.exception("Error loading workbook %s", e)
            break
    raise last_exc


def parse_excel(file_path):
    """
    Parses the Excel file and extracts the required data.
    """
    try:
        workbook = safe_load_excel(file_path)
        sheet = workbook.active

        # Extract all the required data
        work_order_number = sheet["C6"].value
        partner = sheet["B7"].value
        aparat = sheet["B12"].value
        serijski_broj = sheet["E12"].value
        sifra_aparata = sheet["B13"].value
        opis_pogreske = sheet["B16"].value
        opis_obavljenog_posla = sheet["A19"].value
        datum = sheet["E6"].value

        return {
            "work_order_number": work_order_number,
            "partner": partner,
            "aparat": aparat,
            "serijski_broj": serijski_broj,
            "sifra_aparata": sifra_aparata,
            "opis_pogreske": opis_pogreske,
            "opis_obavljenog_posla": opis_obavljenog_posla,
            "datum": datum,
        }

    except FileNotFoundError:
        logging.error(f"Error: The file at {file_path} was not found.")
        return None
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        return None


def generate_details_html(data, output_path="work_order_details.html"):
    """
    Generates an HTML file with the work order details.
    """
    html_content = f"""
<div class="container mt-4">
  <h4>Detalji radnog naloga</h4>
  <table class="table table-striped mt-3">
    <tr>
        <th>Radni nalog</th>
        <td>{data['work_order_number']} <button onclick="copyToClipboard('{data['work_order_number']}')">📋</button></td>
    </tr>
    <tr><th>Partner</th><td>{data['partner']}</td></tr>
    <tr><th>Aparat</th><td>{data['aparat']}</td></tr>
    <tr><th>Serijski broj</th><td>{data['serijski_broj']}</td></tr>
    <tr><th>Šifra aparata</th><td>{data['sifra_aparata']}</td></tr>
    <tr><th>Opis pogreške</th><td>{data['opis_pogreske']}</td></tr>
    <tr><th>Opis obavljenog posla</th><td>{data['opis_obavljenog_posla']}</td></tr>
    <tr>
        <th>Datum</th>
        <td>{data['datum']} <button onclick="copyToClipboard('{data['datum']}')">📋</button></td>
    </tr>
  </table>
</div>
"""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    logging.info(f"Generated {output_path}")


def process_file(file_path, ftp_config, bot_token, chat_id):
    try:
        excel_data = parse_excel(file_path)
        if not excel_data:
            raise ValueError("Could not parse Excel file.")

        radni_nalog = excel_data["work_order_number"]
        datum = excel_data["datum"]
        logging.info("Extracted RN=%s, date=%s", radni_nalog, datum)

        # always override FTP remote file name to data.txt
        ftp_config["remote_file"] = "data.txt"

        server_num = get_current_number_from_ftp(ftp_config)
        try:
            broj_novi = int(str(radni_nalog).split("/")[0].strip())
        except Exception:
            # send_error_message("Ne mogu parsirati broj radnog naloga", file_path, bot_token, chat_id)
            return

        logging.info("Waiting for user confirmation...")

        # waiting_for_reply = False
        # if server_num is not None and broj_novi <= server_num:
        #     waiting_for_reply = True
        #     logging.info("Waiting for user confirmation...")
        #     send_info_message(
        #         f"ℹ️ Čekam korisničku potvrdu za RN: {broj_novi} (na serveru je: {server_num})",
        #         bot_token,
        #         chat_id,
        #         waiting=True,
        #     )
        #     confirmed = ask_confirmation_and_wait(
        #         bot_token,
        #         chat_id,
        #         broj_novi=broj_novi,
        #         broj_stari=server_num,
        #         timeout_seconds=300,
        #     )
        #     if not confirmed:
        #         logging.info("File processing was cancelled or timed out.")
        #         send_info_message(
        #             f"❌ Obrada datoteke {file_path} otkazana od strane korisnika ili je isteklo vrijeme.",
        #             bot_token,
        #             chat_id,
        #             waiting=False,
        #         )
        #         return

        # Proceed if confirmed
        logging.info("User confirmed, proceeding with file upload.")
        save_temp_number(radni_nalog, datum)
        generate_details_html(excel_data)

        files_to_upload = [
            {"local_path": Path("temp_number.txt"), "remote_name": "data.txt"},
            {"local_path": Path("work_order_details.html"), "remote_name": "work_order_details.html"}
        ]

        upload_files_to_ftp(ftp_config, files_to_upload)

        log_data(file_path, radni_nalog, datum)
        # send_success_message(file_path, radni_nalog, datum, bot_token, chat_id)

    except Exception as e:
        logging.exception("Error processing file %s: %s", file_path, e)
        # send_error_message(str(e), file_path, bot_token, chat_id)
