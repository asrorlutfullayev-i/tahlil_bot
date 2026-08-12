import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
ADMIN_ID = os.getenv('ADMIN_ID', '')
DB_PATH = os.getenv('DB_PATH', 'bot_database.db')
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Tashkent')

# Validate required config
if not BOT_TOKEN:
    raise ValueError('BOT_TOKEN topilmadi! .env faylni tekshiring.')
if not GEMINI_API_KEY:
    raise ValueError('GEMINI_API_KEY topilmadi! .env faylni tekshiring.')
