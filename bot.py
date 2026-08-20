import logging
import asyncio
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import BOT_TOKEN
from database import init_db
from handlers.common import cmd_start, cmd_help, cmd_menu, message_router, callback_router
from handlers.reminders import check_reminders_job

# Logging configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database after application starts."""
    logger.info("Database retsini yaratish va tekshirish...")
    await init_db()
    logger.info("Database muvaffaqiyatli ishga tushdi.")


import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK - Bot is running")
    def log_message(self, format, *args):
        return  # Suppress logs for healthchecks

def start_health_server():
    port = int(os.getenv('PORT', 8080))
    server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
    server.serve_forever()

def main():
    """Start the Telegram mentor bot."""
    # Start web healthcheck server if PORT is set (for Render Free Web Service)
    if os.getenv('PORT'):
        threading.Thread(target=start_health_server, daemon=True).start()
        logger.info(f"Health check server started on port {os.getenv('PORT')}")

    # Ensure event loop exists for Python 3.14+
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    logger.info("Bot ishga tushirilmoqda...")

    # Build Application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Add Command Handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("menu", cmd_menu))

    # Add Callback Query Handler (for inline buttons)
    application.add_handler(CallbackQueryHandler(callback_router))

    # Add Message Handler (for menu buttons and text input states)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_router)
    )

    # Job Queue for scheduled reminders (every 60 seconds)
    if application.job_queue:
        application.job_queue.run_repeating(
            check_reminders_job,
            interval=60,
            first=10
        )
        logger.info("Eslatmalar avtomatik tekshiruvchisi ishga tushdi (har 60 sek).")

    # Run bot
    logger.info("Bot tayyor! Xabarlar kutilmoqda...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
