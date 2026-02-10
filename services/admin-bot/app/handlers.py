import json
import logging

import httpx
from telegram import (
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
    WebAppInfo,
)
from telegram.ext import ContextTypes

from app import config

logger = logging.getLogger(__name__)

HTTP_TIMEOUT = 10.0


def _main_keyboard() -> ReplyKeyboardMarkup:
    """Build the main reply keyboard for the admin bot."""
    keyboard = [
        [
            KeyboardButton(
                text="\U0001f4ca \u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0430\u043d\u0435\u043b\u044c \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f",
                web_app=WebAppInfo(url=config.WEBAPP_URL) if config.WEBAPP_URL else None,
            )
        ],
        [
            KeyboardButton(text="\U0001f4c8 \u041c\u0435\u0442\u0440\u0438\u043a\u0438"),
            KeyboardButton(text="\U0001f4e6 \u0417\u0430\u043a\u0430\u0437\u044b"),
        ],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    await update.message.reply_text(
        "\U0001f338 \u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 \u0430\u0434\u043c\u0438\u043d-\u043f\u0430\u043d\u0435\u043b\u044c "
        "\u0446\u0432\u0435\u0442\u043e\u0447\u043d\u043e\u0433\u043e \u043c\u0430\u0433\u0430\u0437\u0438\u043d\u0430!\n\n"
        "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 \u043a\u043d\u043e\u043f\u043a\u0438 \u043d\u0438\u0436\u0435 \u0434\u043b\u044f \u0443\u043f\u0440\u0430\u0432\u043b\u0435\u043d\u0438\u044f:",
        reply_markup=_main_keyboard(),
    )


async def metrics_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch analytics dashboard data and display a formatted summary."""
    await update.message.reply_text("\u23f3 \u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043c\u0435\u0442\u0440\u0438\u043a...")

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(
                f"{config.ANALYTICS_SERVICE_URL}/analytics/dashboard"
            )
            response.raise_for_status()
            data = response.json()

        total_orders = data.get("total_orders", 0)
        total_revenue = data.get("total_revenue", 0)
        average_order = data.get("avg_order_value", 0)
        today_orders = data.get("orders_today", 0)

        top_by_views = data.get("popular_by_views", [])
        top_by_orders = data.get("popular_by_orders", [])

        lines = [
            "\U0001f4c8 \u041c\u0435\u0442\u0440\u0438\u043a\u0438 \u043c\u0430\u0433\u0430\u0437\u0438\u043d\u0430",
            "\u2500" * 24,
            f"\U0001f4e6 \u0412\u0441\u0435\u0433\u043e \u0437\u0430\u043a\u0430\u0437\u043e\u0432: {total_orders}",
            f"\U0001f4b0 \u041e\u0431\u0449\u0430\u044f \u0432\u044b\u0440\u0443\u0447\u043a\u0430: {total_revenue:.2f} \u0440\u0443\u0431.",
            f"\U0001f4b3 \u0421\u0440\u0435\u0434\u043d\u0438\u0439 \u0447\u0435\u043a: {average_order:.2f} \u0440\u0443\u0431.",
            f"\U0001f4c5 \u0417\u0430\u043a\u0430\u0437\u043e\u0432 \u0441\u0435\u0433\u043e\u0434\u043d\u044f: {today_orders}",
            "",
        ]

        if top_by_views:
            lines.append(
                "\U0001f441 \u0422\u043e\u043f-5 \u043f\u043e \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430\u043c:"
            )
            for i, product in enumerate(top_by_views[:5], start=1):
                name = product.get("product_name", "\u2014")
                views = product.get("view_count", 0)
                lines.append(f"  {i}. {name} \u2014 {views} \u043f\u0440\u043e\u0441\u043c.")
            lines.append("")

        if top_by_orders:
            lines.append(
                "\U0001f6d2 \u0422\u043e\u043f-5 \u043f\u043e \u0437\u0430\u043a\u0430\u0437\u0430\u043c:"
            )
            for i, product in enumerate(top_by_orders[:5], start=1):
                name = product.get("product_name", "\u2014")
                orders_count = product.get("order_count", 0)
                lines.append(f"  {i}. {name} \u2014 {orders_count} \u0437\u0430\u043a.")
            lines.append("")

        await update.message.reply_text("\n".join(lines))

    except httpx.HTTPStatusError as exc:
        logger.error("Analytics service returned error: %s", exc.response.status_code)
        await update.message.reply_text(
            "\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043c\u0435\u0442\u0440\u0438\u043a\u0438. "
            "\u0421\u0435\u0440\u0432\u0438\u0441 \u0430\u043d\u0430\u043b\u0438\u0442\u0438\u043a\u0438 \u0432\u0435\u0440\u043d\u0443\u043b \u043e\u0448\u0438\u0431\u043a\u0443."
        )
    except Exception:
        logger.exception("Failed to fetch metrics")
        await update.message.reply_text(
            "\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043c\u0435\u0442\u0440\u0438\u043a\u0438. "
            "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
        )


_ORDER_STATUS_LABELS = {
    "pending": "\u23f3 \u041e\u0436\u0438\u0434\u0430\u0435\u0442",
    "confirmed": "\u2705 \u041f\u043e\u0434\u0442\u0432\u0435\u0440\u0436\u0434\u0451\u043d",
    "preparing": "\U0001f528 \u0413\u043e\u0442\u043e\u0432\u0438\u0442\u0441\u044f",
    "ready": "\U0001f4e6 \u0413\u043e\u0442\u043e\u0432",
    "delivering": "\U0001f69a \u0414\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0435\u0442\u0441\u044f",
    "completed": "\u2705 \u0417\u0430\u0432\u0435\u0440\u0448\u0451\u043d",
    "cancelled": "\u274c \u041e\u0442\u043c\u0435\u043d\u0451\u043d",
}


async def orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch recent orders from the order service and display them."""
    await update.message.reply_text(
        "\u23f3 \u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0437\u0430\u043a\u0430\u0437\u043e\u0432..."
    )

    try:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
            response = await client.get(f"{config.ORDER_SERVICE_URL}/orders/")
            response.raise_for_status()
            orders = response.json()

        if not orders:
            await update.message.reply_text(
                "\U0001f4ed \u0417\u0430\u043a\u0430\u0437\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442."
            )
            return

        # Show up to 10 most recent orders
        recent = orders[:10] if isinstance(orders, list) else []
        if not recent:
            await update.message.reply_text(
                "\U0001f4ed \u0417\u0430\u043a\u0430\u0437\u043e\u0432 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442."
            )
            return

        lines = [
            "\U0001f4e6 \u041f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u0437\u0430\u043a\u0430\u0437\u044b:",
            "\u2500" * 24,
        ]
        for order in recent:
            order_id = order.get("id", "?")
            status_raw = order.get("status", "unknown")
            status_label = _ORDER_STATUS_LABELS.get(status_raw, status_raw)
            total = order.get("total_amount", 0)
            created = order.get("created_at", "")[:16].replace("T", " ")
            lines.append(
                f"\u2022 #{order_id}  {status_label}\n"
                f"  \u0421\u0443\u043c\u043c\u0430: {total} \u0440\u0443\u0431. | {created}"
            )

        await update.message.reply_text("\n".join(lines))

    except httpx.HTTPStatusError as exc:
        logger.error("Order service returned error: %s", exc.response.status_code)
        await update.message.reply_text(
            "\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0437\u0430\u043a\u0430\u0437\u044b. "
            "\u0421\u0435\u0440\u0432\u0438\u0441 \u0437\u0430\u043a\u0430\u0437\u043e\u0432 \u0432\u0435\u0440\u043d\u0443\u043b \u043e\u0448\u0438\u0431\u043a\u0443."
        )
    except Exception:
        logger.exception("Failed to fetch orders")
        await update.message.reply_text(
            "\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0437\u0430\u043a\u0430\u0437\u044b. "
            "\u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
        )


async def web_app_data_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle data received from the admin WebApp."""
    try:
        raw_data = update.effective_message.web_app_data.data
        data = json.loads(raw_data)
        action = data.get("action", "unknown")

        if action == "product_update":
            product_name = data.get("name", "\u0442\u043e\u0432\u0430\u0440")
            await update.message.reply_text(
                f"\u2705 \u0422\u043e\u0432\u0430\u0440 \u00ab{product_name}\u00bb "
                "\u0443\u0441\u043f\u0435\u0448\u043d\u043e \u043e\u0431\u043d\u043e\u0432\u043b\u0451\u043d."
            )
        elif action == "product_add":
            product_name = data.get("name", "\u0442\u043e\u0432\u0430\u0440")
            await update.message.reply_text(
                f"\u2705 \u0422\u043e\u0432\u0430\u0440 \u00ab{product_name}\u00bb "
                "\u0443\u0441\u043f\u0435\u0448\u043d\u043e \u0434\u043e\u0431\u0430\u0432\u043b\u0435\u043d."
            )
        elif action == "product_delete":
            product_name = data.get("name", "\u0442\u043e\u0432\u0430\u0440")
            await update.message.reply_text(
                f"\u2705 \u0422\u043e\u0432\u0430\u0440 \u00ab{product_name}\u00bb \u0443\u0434\u0430\u043b\u0451\u043d."
            )
        elif action == "availability_update":
            product_name = data.get("name", "\u0442\u043e\u0432\u0430\u0440")
            available = data.get("available", False)
            status = (
                "\u0432 \u043d\u0430\u043b\u0438\u0447\u0438\u0438"
                if available
                else "\u043d\u0435\u0442 \u0432 \u043d\u0430\u043b\u0438\u0447\u0438\u0438"
            )
            await update.message.reply_text(
                f"\u2705 \u0422\u043e\u0432\u0430\u0440 \u00ab{product_name}\u00bb \u2014 {status}."
            )
        else:
            await update.message.reply_text(
                f"\u2705 \u0414\u0430\u043d\u043d\u044b\u0435 \u043f\u043e\u043b\u0443\u0447\u0435\u043d\u044b (action={action})."
            )

    except json.JSONDecodeError:
        logger.warning("Received invalid JSON from WebApp")
        await update.message.reply_text(
            "\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0435 "
            "\u0434\u0430\u043d\u043d\u044b\u0445 \u0438\u0437 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f."
        )
    except Exception:
        logger.exception("Error processing WebApp data")
        await update.message.reply_text(
            "\u274c \u041f\u0440\u043e\u0438\u0437\u043e\u0448\u043b\u0430 \u043e\u0448\u0438\u0431\u043a\u0430 "
            "\u043f\u0440\u0438 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0435 \u0434\u0430\u043d\u043d\u044b\u0445."
        )
