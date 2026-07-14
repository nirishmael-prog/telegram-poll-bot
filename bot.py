# -*- coding: utf-8 -*-
"""
בוט טלגרם ששולח כל יום, בשעה קבועה, אחד מבין: סקר קבוע, חידון קבוע,
או שאלה שנוצרת ע"י Claude (אופציונלי) - הכל לפי אזור זמן נכון.
"""

import os
import json
import random
import logging
import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Poll
from telegram.ext import Application, ContextTypes
from dotenv import load_dotenv

from topics import FIXED_POLLS, QUIZ_POLLS

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
SEND_HOUR = int(os.getenv("SEND_HOUR", "9"))
SEND_MINUTE = int(os.getenv("SEND_MINUTE", "0"))
TIMEZONE = os.getenv("TIMEZONE", "Asia/Jerusalem")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

USED_POLLS_FILE = Path(__file__).parent / "used_topics.json"
USED_QUIZZES_FILE = Path(__file__).parent / "used_quizzes.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _load_used(path: Path) -> list:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return []


def _save_used(path: Path, used: list) -> None:
    path.write_text(json.dumps(used, ensure_ascii=False), encoding="utf-8")


def get_fixed_poll() -> dict:
    used = _load_used(USED_POLLS_FILE)
    remaining = [p for p in FIXED_POLLS if p[0] not in used]
    if not remaining:
        used = []
        remaining = FIXED_POLLS
    question, options = random.choice(remaining)
    used.append(question)
    _save_used(USED_POLLS_FILE, used)
    return {"question": question, "options": options, "is_quiz": False}


def get_quiz_poll() -> dict:
    used = _load_used(USED_QUIZZES_FILE)
    remaining = [q for q in QUIZ_POLLS if q[0] not in used]
    if not remaining:
        used = []
        remaining = QUIZ_POLLS
    question, options, correct_index = random.choice(remaining)
    used.append(question)
    _save_used(USED_QUIZZES_FILE, used)
    return {"question": question, "options": options, "is_quiz": True, "correct_index": correct_index}


def get_ai_poll() -> dict | None:
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
        return {"question": data["question"], "options": data["options"], "is_quiz": False}
    except Exception as e:
        logger.warning("AI poll generation failed, falling back to fixed list: %s", e)
        return None


def get_daily_poll() -> dict:
    roll = random.random()

    if roll < 0.20:
        return get_quiz_poll()

    if ANTHROPIC_API_KEY and roll < 0.60:
        ai_result = get_ai_poll()
        if ai_result:
            return ai_result

    return get_fixed_poll()


async def send_daily_poll(context: ContextTypes.DEFAULT_TYPE) -> None:
    item = get_daily_poll()

    kwargs = dict(
        chat_id=CHAT_ID,
        options=item["options"],
        is_anonymous=False,
        allows_multiple_answers=False,
    )

    if item["is_quiz"]:
        kwargs["question"] = f"🧠 חידון היום: {item['question']}"
        kwargs["type"] = Poll.QUIZ
        kwargs["correct_option_id"] = item["correct_index"]
    else:
        kwargs["question"] = f"📊 סקר היום: {item['question']}"

    await context.bot.send_poll(**kwargs)
    logger.info("Sent %s: %s", "quiz" if item["is_quiz"] else "poll", item["question"])


def main() -> None:
    if not BOT_TOKEN or not CHAT_ID:
        raise RuntimeError("חסר BOT_TOKEN או CHAT_ID בקובץ .env - ראה README.md")

    app = Application.builder().token(BOT_TOKEN).build()

    app.job_queue.run_daily(
        send_daily_poll,
        time=datetime.time(hour=SEND_HOUR, minute=SEND_MINUTE, tzinfo=ZoneInfo(TIMEZONE)),
    )

    logger.info("Bot started. Daily send scheduled at %02d:%02d (%s).", SEND_HOUR, SEND_MINUTE, TIMEZONE)
    app.run_polling()


if __name__ == "__main__":
    main()
