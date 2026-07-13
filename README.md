# בוט סקרים יומיומי לטלגרם

בוט ששולח כל יום, בשעה קבועה, סקר קליל לקבוצה - חלק מהזמן מרשימה קבועה
(`topics.py`), חלק מהזמן שאלה חדשה שמייצר Claude (אופציונלי).

## שלב 1: יצירת הבוט ב-BotFather

1. פתחו שיחה עם [@BotFather](https://t.me/BotFather) בטלגרם.
2. שלחו `/newbot`, תנו לו שם ושם משתמש (חייב להסתיים ב-`bot`).
3. תקבלו **טוקן** (משהו כמו `123456:ABC-DEF...`) - זה ה-`BOT_TOKEN`.

## שלב 2: הוספת הבוט לקבוצה + מציאת CHAT_ID

1. הוסיפו את הבוט לקבוצה הרצויה.
2. שלחו הודעה כלשהי בקבוצה.
3. גשו לכתובת (בדפדפן, אחרי החלפת `<TOKEN>`):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. חפשו בתשובה את `"chat":{"id": -100...}` - זה ה-`CHAT_ID`.

## שלב 3: הרצה 24/7 ב-Railway

1. גשו ל-https://railway.app והתחברו עם GitHub.
2. New Project → Deploy from GitHub repo → בחרו את ה-repo הזה.
3. בהגדרות הפרויקט (Variables) הוסיפו: BOT_TOKEN, CHAT_ID, SEND_HOUR,
   SEND_MINUTE, TIMEZONE, ANTHROPIC_API_KEY (אופציונלי).
4. Railway יזהה את ה-`Procfile` ויריץ את הבוט אוטומטית, כל הזמן.

## התאמות קלות

- **סקר אנונימי**: שנו `is_anonymous=False` ל-`True` ב-`bot.py`.
- **יחס AI מול קבוע**: שנו את `0.5` בפונקציה `get_daily_poll` ב-`bot.py`.
