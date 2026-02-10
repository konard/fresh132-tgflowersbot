"""Main entry point for the customer-facing Telegram flower shop bot."""

import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app.config import BOT_TOKEN, WEBAPP_URL
from app.handlers import (
    help_command,
    location_handler,
    my_orders_handler,
    start_command,
    web_app_data_handler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Build the Application, register handlers and start polling."""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set.")
        sys.exit(1)

    if not WEBAPP_URL:
        logger.warning(
            "WEBAPP_URL environment variable is not set. "
            "The catalog button will not work correctly."
        )

    application = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))

    # Location handler -- fires when user shares their location
    application.add_handler(MessageHandler(filters.LOCATION, location_handler))

    # WebApp data handler -- fires when WebApp sends data back to the bot
    application.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    # Text handler for the "My orders" keyboard button
    application.add_handler(
        MessageHandler(
            filters.Text(["\U0001f4e6 \u041c\u043e\u0438 \u0437\u0430\u043a\u0430\u0437\u044b"]),
            my_orders_handler,
        )
    )

    logger.info("Bot is starting in polling mode...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
