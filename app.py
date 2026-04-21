import os
import time
import requests
from telegram import Bot
from telegram.error import TelegramError

# Чтение конфигурации из переменных окружения (для облачных сервисов)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TWITCH_CLIENT_ID = os.environ.get("TWITCH_CLIENT_ID")
TWITCH_OAUTH_TOKEN = os.environ.get("TWITCH_OAUTH_TOKEN")
TWITCH_USER_LOGIN = os.environ.get("TWITCH_USER_LOGIN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")  # например, "@your_channel" или числовой ID

# Проверка обязательных переменных
missing = [k for k, v in {
    "TELEGRAM_BOT_TOKEN": TELEGRAM_BOT_TOKEN,
    "TWITCH_CLIENT_ID": TWITCH_CLIENT_ID,
    "TWITCH_OAUTH_TOKEN": TWITCH_OAUTH_TOKEN,
    "TWITCH_USER_LOGIN": TWITCH_USER_LOGIN,
    "TELEGRAM_CHAT_ID": TELEGRAM_CHAT_ID,
}.items() if not v]

if missing:
    raise SystemExit(f"Не заданы обязательные переменные окружения: {', '.join(missing)}")

# Инициализация клиента Telegram
bot = Bot(token=TELEGRAM_BOT_TOKEN)

headers = {
    "Client-ID": TWITCH_CLIENT_ID,
    "Authorization": f"Bearer {TWITCH_OAUTH_TOKEN}"
}

def get_stream_status(user_login: str):
    url = f"https://api.twitch.tv/helix/streams?user_login={user_login}"
    resp = requests.get(url, headers=headers, timeout=10)
    if resp.status_code != 200:
        print(f"Ошибка Twitch API: {resp.status_code} {resp.text}")
        return None
    data = resp.json()
    streams = data.get("data", [])
    if not streams:
        return None
    return streams[0]  # активный стрим

def main_loop(poll_interval=60):
    last_stream_id = None
    last_message_id = None  # id сообщения, которое мы создали в Telegram
    while True:
        try:
            stream = get_stream_status(TWITCH_USER_LOGIN)
            if stream:
                # Стрим идет
                stream_id = stream.get("id")
                if stream_id != last_stream_id:
                    # Новый старт стрима или снова запущен
                    user_display = stream.get("user_name", TWITCH_USER_LOGIN)
                    title = stream.get("title", "")
                    twitch_url = f"https://www.twitch.tv/{TWITCH_USER_LOGIN}"
                    message_text = f"Стрим запущен: {user_display} — {title}\n{twitch_url}"

                    # Удаление старого уведомления, если нужно
                    if last_message_id is not None:
                        try:
                            bot.delete_message(chat_id=TELEGRAM_CHAT_ID, message_id=last_message_id)
                        except TelegramError as e:
                            print(f"Не удалось удалить прошлое сообщение: {e}")

                    try:
                        sent = bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message_text)
                        last_message_id = sent.message_id
                    except TelegramError as e:
                        print(f"Ошибка отправки: {e}")
                        last_message_id = None

                    last_stream_id = stream_id
            else:
                # Нет активного стрима
                if last_stream_id is not None:
                    # Стрим закончился: удаляем уведомление, если оно было
                    if last_message_id is not None:
                        try:
                            bot.delete_message(chat_id=TELEGRAM_CHAT_ID, message_id=last_message_id)
                        except TelegramError as e:
                            print(f"Ошибка удаления сообщения по окончании стрима: {e}")
                        last_message_id = None
                    last_stream_id = None
        except Exception as e:
            print(f"Ошибка цикла: {e}")

        time.sleep(poll_interval)

if __name__ == "__main__":
    main_loop(poll_interval=60)