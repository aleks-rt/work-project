import logging
import webbrowser
import time
import json
import os
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from config import DB_PATH

logger = logging.getLogger(__name__)

# Регистрируем приложение на dev.hh.ru и получаем эти данные
# Используем публичные credentials от open-source клиентов
HH_CLIENT_ID = "APPDVQAPJF37CPBBNT0IVAG2HJF53BDEBQF72JIVTNJ1H1T5JISFTGJJ3UFVUIV"
HH_CLIENT_SECRET = "IQKPHHF9AVD7NBMGV72OPAI5UDLEF1FJDPE58KICBN6JVNPB5UVR4JBCIMFFCKB"
HH_REDIRECT_URI = "http://localhost:12345/callback"
TOKEN_FILE = "hh_token.json"

HEADERS = {
    "User-Agent": "hh-applicant-tool/1.0 (github.com/s3rgeym/hh-applicant-tool)",
    "Accept": "application/json",
}


class _CallbackHandler(BaseHTTPRequestHandler):
    code = None

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            _CallbackHandler.code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write("<h2>Avtorizatsiya uspeshna! Mozhno zakryt vkladku.</h2>".encode())
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, *args):
        pass


def get_auth_url() -> str:
    return (
        f"https://hh.ru/oauth/authorize"
        f"?response_type=code"
        f"&client_id={HH_CLIENT_ID}"
        f"&redirect_uri={HH_REDIRECT_URI}"
    )


def exchange_code(code: str) -> dict:
    resp = requests.post(
        "https://hh.ru/oauth/token",
        data={
            "grant_type": "authorization_code",
            "client_id": HH_CLIENT_ID,
            "client_secret": HH_CLIENT_SECRET,
            "redirect_uri": HH_REDIRECT_URI,
            "code": code,
        },
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def refresh_token(refresh_tok: str) -> dict:
    resp = requests.post(
        "https://hh.ru/oauth/token",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
        },
        headers=HEADERS,
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def save_token(token_data: dict):
    token_data["saved_at"] = time.time()
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f)


def load_token() -> dict | None:
    if not os.path.exists(TOKEN_FILE):
        return None
    with open(TOKEN_FILE) as f:
        return json.load(f)


def get_valid_token() -> str | None:
    data = load_token()
    if not data:
        return None
    # Обновляем если токен протух (expires_in секунд)
    age = time.time() - data.get("saved_at", 0)
    if age > data.get("expires_in", 86400) - 300:
        try:
            data = refresh_token(data["refresh_token"])
            save_token(data)
        except Exception as e:
            logger.error("Token refresh failed: %s", e)
            return None
    return data["access_token"]


def authorize_interactive() -> str:
    """Открывает браузер для авторизации и ждёт callback. Возвращает access_token."""
    url = get_auth_url()
    print(f"\nОткройте ссылку в браузере для авторизации hh.ru:\n{url}\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 12345), _CallbackHandler)
    print("Ожидаю авторизацию...")
    while _CallbackHandler.code is None:
        server.handle_request()

    code = _CallbackHandler.code
    token_data = exchange_code(code)
    save_token(token_data)
    print("Авторизация успешна! Токен сохранён.")
    return token_data["access_token"]


def get_my_resumes(token: str) -> list[dict]:
    resp = requests.get(
        "https://api.hh.ru/resumes/mine",
        headers={**HEADERS, "Authorization": f"Bearer {token}"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def apply_to_vacancy(token: str, vacancy_id: str, resume_id: str, message: str = "") -> dict:
    data = {"vacancy_id": vacancy_id, "resume_id": resume_id}
    if message:
        data["message"] = message
    resp = requests.post(
        "https://api.hh.ru/negotiations",
        headers={**HEADERS, "Authorization": f"Bearer {token}"},
        data=data,
        timeout=15,
    )
    return {"status": resp.status_code, "body": resp.text}
