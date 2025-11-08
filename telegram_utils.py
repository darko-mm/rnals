# =======================
# File: telegram_utils.py
# =======================
"""
Telegram helpers. send messages and ask_confirmation_and_wait which polls getUpdates.
"""
import requests
import time
import logging

API_URL = "https://api.telegram.org/bot{token}/{method}"


def _request(token, method, data=None, files=None, timeout=10):
    url = API_URL.format(token=token, method=method)
    r = requests.post(url, data=data, files=files, timeout=timeout)
    r.raise_for_status()
    return r.json()


def send_message(token, chat_id, text, parse_mode="HTML"):
    data = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    try:
        return _request(token, "sendMessage", data=data)
    except Exception as e:
        logging.warning("Telegram sendMessage failed: %s", e)


def send_info_message(text, token, chat_id, waiting=False):
    """General info log to Telegram."""
    suffix = " (waiting for user reply...)" if waiting else ""
    msg = f"{text}{suffix}"
    send_message(token, chat_id, msg)
    logging.info("Sent Telegram info message%s", suffix)


def send_success_message(file_name, radni_nalog, datum, token, chat_id):
    now = time.strftime("%d.%m.%Y %H:%M:%S")
    text = (
        f"✅ <b>Obrada uspješno završena</b>\n\n"
        f"<b>Datum</b>: {now}\n"
        f"<b>Radni nalog</b>: {radni_nalog}\n"
        f"<b>Datum u Excelu</b>: {datum}\n"
        f"<b>Excel datoteka</b>: {file_name}\n\n"
        "Podaci su uspješno poslani na FTP server."
    )
    send_message(token, chat_id, text)


def send_error_message(error_message, file_path, token, chat_id):
    now = time.strftime("%d.%m.%Y %H:%M:%S")
    text = (
        f"❌ <b>Greška pri obradi!</b>\n\n"
        f"<b>Datum</b>: {now}\n"
        f"<b>Datoteka</b>: {file_path}\n"
        f"<b>Greška</b>: {error_message}\n\n"
        "Obrada nije uspjela, provjerite logove."
    )
    send_message(token, chat_id, text)

def discard_old_updates(token):
    """Discard any old pending updates before waiting for a new reply."""
    url = API_URL.format(token=token, method="getUpdates")
    try:
        response = requests.get(url, params={"timeout": 0})
        response.raise_for_status()
        data = response.json()
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                last_id = updates[-1]["update_id"]
                # Discard all previous updates
                requests.get(url, params={"offset": last_id + 1, "timeout": 0})
    except Exception as e:
        logging.warning("Failed to discard old updates: %s", e)

def ask_confirmation_and_wait(token, chat_id, broj_novi, broj_stari, timeout_seconds=300, poll_interval=3):
    """Send warning and poll for 'da'/'d' or 'ne'/'n'."""
    
    # 🧹 Pocisti queue starih poruka
    discard_old_updates(token)
    
    text = (
        f"⚠️ <b>Upozorenje!</b>\n\n"
        f"<b>Novi broj</b>: {str(broj_novi).zfill(4)}\n"
        f"<b>Stari broj na serveru</b>: {str(broj_stari).zfill(4)}\n\n"
        "Novi broj je manji ili jednak broju na serveru. "
        "Pošaljite 'da' ili 'd' za nastavak, 'ne' ili 'n' za prekid."
    )
    send_message(token, chat_id, text)

    offset = None  # Track the offset
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            params = {"timeout": 5}
            if offset:
                params["offset"] = offset  # Continue from last update
            url = API_URL.format(token=token, method="getUpdates")
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            data = r.json()

            if not data.get("ok"):
                time.sleep(poll_interval)
                continue

            updates = data.get("result", [])
            for upd in updates:
                offset = max(offset or 0, upd["update_id"] + 1)  # Update the offset
                msg = upd.get("message")
                if not msg:
                    continue
                if str(msg.get("chat", {}).get("id")) != str(chat_id):
                    continue
                txt = (msg.get("text") or "").strip().lower()
                if txt in ("da", "d"):
                    send_info_message("✅ Korisnik potvrdio nastavak.", token, chat_id)
                    return True
                if txt in ("ne", "n"):
                    send_info_message("🚫 Korisnik odbio nastavak.", token, chat_id)
                    return False
            time.sleep(poll_interval)
        except Exception as e:
            logging.warning("Polling Telegram updates failed: %s", e)
            time.sleep(poll_interval)

    send_info_message("⏰ Nije stigla potvrda na vrijeme. Obrada otkazana.", token, chat_id)
    return False
