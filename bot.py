# -*- coding: utf-8 -*-
"""
בוט טלגרם ששולח סקר יומיומי לקבוצה - בשעה קבועה, כל יום.
חצי מהזמן שולף שאלה מרשימה קבועה (topics.py), חצי מהזמן מבקש מ-Claude
לחדש שאלה. שומר קובץ used_topics.json כדי לא לחזור על אותה שאלה קבועה
פעמיים ברצף עד שעברנו על כל הרשימה.

הפעלה:
    python bot.py
"""

import os
import json
import random
import logging
from pathlib import Path

from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv

from topics import FIXED_POLLS

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")  # ה-ID של הקבוצה (יכול להיות שלילי, למשל -1001234567890)
SEND_HOUR = int(os.getenv("SEND_HOUR", "9"))    # שעה לשליחה (24h)
SEND_MINUTE = int(os.getenv("SEND_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jerusalem")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")  # אופציונלי - בלי זה ישתמש רק ברשימה הקבועה

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
    """מחזיר שאלה קבועה שעוד לא נשאלה (ומתחיל סבב חדש כשהרשימה נגמרת)."""
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
    """מבקש מ-Claude שאלת סקר יומיומית וקלילה, מחזיר (שאלה, אפשרויות) או None אם נכשל."""
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
    """שילוב: ~50% AI (אם מוגדר מפתח), ~50% מהרשימה הקבועה."""
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
        is_anonymous=False,   # שינוי ל-True אם רוצים סקר אנונימי
        allows_multiple_answers=False,
    )
    logger.info("Poll sent: %s", question)


def main() -> None:
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("חסר BOT_TOKEN או CHAT_ID בקובץ .env - ראה README.md")

    app = Application.builder().token(BOT_TOKEN).build()

    # תזמון יומי בשעה קבועה
    app.job_queue.run_daily(
        send_daily_poll,
        time=__import__("datetime").time(hour=SEND_HOUR, minute=SEND_MINUTE),
    )

    logger.info("Bot started. Daily poll scheduled at %02d:%02d (%s).", SEND_HOUR, SEND_MINUTE, TIMEZONE)
    app.run_polling()


if __name__ == "__main__":
    main()
