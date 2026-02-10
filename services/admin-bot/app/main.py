"""Admin Telegram bot for the flower shop.

Provides administrators with:
- A WebApp button to open the product management panel
- Metrics and analytics from the analytics service
- Recent orders overview from the order service
"""

import logging
import sys

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from app import config
from app.handlers import (
    metrics_handler,
    orders_handler,
    start_command,
    web_app_data_handler,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    """Build the application, register handlers, and start polling."""
    if not config.BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable is not set")
        sys.exit(1)

    if not config.WEBAPP_URL:
        logger.warning(
            "WEBAPP_URL environment variable is not set; "
            "the admin panel button will not open a WebApp"
        )

    application = Application.builder().token(config.BOT_TOKEN).build()

    # /start command
    application.add_handler(CommandHandler("start", start_command))

    # Text-based menu buttons
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^.*\u041c\u0435\u0442\u0440\u0438\u043a\u0438$"),
            metrics_handler,
        )
    )
    application.add_handler(
        MessageHandler(
            filters.Regex(r"^.*\u0417\u0430\u043a\u0430\u0437\u044b$"),
            orders_handler,
        )
    )

    # Data sent back from the admin WebApp
    application.add_handler(
        MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler)
    )

    logger.info("Admin bot is starting in polling mode...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
