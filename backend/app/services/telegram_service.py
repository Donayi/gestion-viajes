import json
import logging
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.core.config import settings


logger = logging.getLogger(__name__)


def send_telegram_message(text: str, chat_id: str | None = None) -> bool:
    if not settings.telegram_enabled:
        return False

    token = settings.telegram_bot_token
    target_chat_id = chat_id or settings.telegram_default_chat_id
    if not token or not target_chat_id:
        logger.warning("Telegram no configurado completamente: falta bot token o chat_id")
        return False

    payload = json.dumps(
        {
            "chat_id": target_chat_id,
            "text": text,
            "disable_web_page_preview": False,
        }
    ).encode("utf-8")
    request = Request(
        url=f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.exception("Error enviando mensaje a Telegram: %s", exc)
        return False
