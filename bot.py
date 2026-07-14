# -*- coding: utf-8 -*-
"""
בוט טלגרם ששולח סקר יומיומי לקבוצה - בשעה קבועה, כל יום, לפי אזור הזמן שהוגדר.
"""

import os
import json
import random
import logging
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv

from topics import FIXED_POLLS

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SEND_HOUR = int(os.getenv("SEND_HOUR", "9"))
SEND_MINUTE = int(os.getenv("SEND_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jerusalem")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

USED_FILE = Path(__file__).parent / "used_topics.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _load_used() -> list:
    if USED_FILE.exists():
        return json.loads(USED_FILE.read_text(encoding="utf-8"))
    return []


def _save_used(used: list) -> None:
    USED_FILE.write_text(json.dumps(used, ensure_ascii=False), encoding="utf-8")


def get_fixed_poll() -> tuple:
    used = _load_used()
    remaining = [p for p in FIXED_POLLS if p[0] not in used]
    if not remaining:
        used = []
        remaining = FIXED_POLLS
    question, options = random.choice(remaining)
    used.append(question)
    _save_used(used)
    return question, options


def get_ai_poll() -> tuple | None:
    if not ANTHROPIC_API_KEY:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{
                "role": "user",
                "content": (
                    "תן לי שאלת סקר יומיומית קלילה וכיפית בעברית, עם 2 עד 4 אפשרויות תשובה קצרות. "
                    "נושאים אפשריים: הרגלים, אוכל, מצב רוח, זמן פנוי, דעות קלילות על החיים. "
                    "החזר אך ורק JSON תקני בפורמט הזה, בלי שום טקסט נוסף: "
                    '{"question": "...", "options": ["...", "..."]}'
                ),
            }],
        )
        text = msg.content[0].text.strip()
        text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(text)
        return data["question"], data["options"]
    except Exception as e:
        logger.warning("AI poll generation failed, falling back to fixed list: %s", e)
        return None


def get_daily_poll() -> tuple:
    if ANTHROPIC_API_KEY and random.random() < 0.5:
        ai_result = get_ai_poll()
        if ai_result:
            return ai_result
    return get_fixed_poll()


async def send_daily_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    question, options = get_daily_poll()
    await context.bot.send_poll(
        chat_id=CHAT_ID,
        question=f"📊 סקר היום: {question}",
        options=options,
        is_anonymous=False,
        allows_multiple_answers=False,
    )
    logger.info("Poll sent: %s", question)


def main() -> None:
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("חסר BOT_TOKEN או CHAT_ID בקובץ .env - ראה README.md")

    app = Application.builder().token(BOT_TOKEN).build()

    app.job_queue.run_daily(
        send_daily_poll,
        time=datetime.time(hour=SEND_HOUR, minute=SEND_MINUTE, tzinfo=ZoneInfo(TIMEZONE)),
    )

    logger.info("Bot started. Daily poll scheduled at %02d:%02d (%s).", SEND_HOUR, SEND_MINUTE, TIMEZONE)
    app.run_polling()


if __name__ == "__main__":
    main()
