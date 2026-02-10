"""Telegram bot handlers for the customer-facing flower shop bot."""

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

from app.config import CATALOG_SERVICE_URL, ORDER_SERVICE_URL, WEBAPP_URL

logger = logging.getLogger(__name__)

# In-memory storage for user locations keyed by Telegram user id.
user_locations: dict[int, dict[str, float]] = {}


def _main_keyboard() -> ReplyKeyboardMarkup:
    """Build the main reply keyboard shown to every user."""
    keyboard = [
        [KeyboardButton(
            text="\U0001f6d2 \u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u0442\u0430\u043b\u043e\u0433",
            web_app=WebAppInfo(url=WEBAPP_URL),
        )],
        [KeyboardButton(
            text="\U0001f4cd \u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043c\u0435\u0441\u0442\u043e\u043f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u0435",
            request_location=True,
        )],
        [KeyboardButton(text="\U0001f4e6 \u041c\u043e\u0438 \u0437\u0430\u043a\u0430\u0437\u044b")],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command -- greet user and show the main keyboard."""
    user = update.effective_user
    if user is None or update.message is None:
        return

    welcome_text = (
        f"\u041f\u0440\u0438\u0432\u0435\u0442, {user.first_name}! \U0001f338\n\n"
        "\u0414\u043e\u0431\u0440\u043e \u043f\u043e\u0436\u0430\u043b\u043e\u0432\u0430\u0442\u044c \u0432 \u043d\u0430\u0448 \u0446\u0432\u0435\u0442\u043e\u0447\u043d\u044b\u0439 \u043c\u0430\u0433\u0430\u0437\u0438\u043d!\n\n"
        "\U0001f4cd \u041e\u0442\u043f\u0440\u0430\u0432\u044c\u0442\u0435 \u0441\u0432\u043e\u0451 \u043c\u0435\u0441\u0442\u043e\u043f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0434\u043b\u044f \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438\n"
        "\U0001f6d2 \u041e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043a\u0430\u0442\u0430\u043b\u043e\u0433, \u0447\u0442\u043e\u0431\u044b \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0446\u0432\u0435\u0442\u044b\n"
        "\U0001f4e6 \u041f\u043e\u0441\u043c\u043e\u0442\u0440\u0438\u0442\u0435 \u0441\u0432\u043e\u0438 \u0437\u0430\u043a\u0430\u0437\u044b"
    )

    await update.message.reply_text(welcome_text, reply_markup=_main_keyboard())


# ---------------------------------------------------------------------------
# /help
# ---------------------------------------------------------------------------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command -- display usage instructions."""
    if update.message is None:
        return

    help_text = (
        "\U0001f4d6 *\u0418\u043d\u0441\u0442\u0440\u0443\u043a\u0446\u0438\u044f*\n\n"
        "1\\. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 *\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043c\u0435\u0441\u0442\u043e\u043f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u0435* \u0434\u043b\u044f \u0443\u043a\u0430\u0437\u0430\u043d\u0438\u044f \u0430\u0434\u0440\u0435\u0441\u0430 \u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0438\\.\n"
        "2\\. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 *\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u0442\u0430\u043b\u043e\u0433* \u0434\u043b\u044f \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430 \u0442\u043e\u0432\u0430\u0440\u043e\u0432\\.\n"
        "3\\. \u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0442\u043e\u0432\u0430\u0440\u044b, \u0434\u043e\u0431\u0430\u0432\u044c\u0442\u0435 \u0438\u0445 \u0432 \u043a\u043e\u0440\u0437\u0438\u043d\u0443\\.\n"
        "4\\. \u041f\u0435\u0440\u0435\u0439\u0434\u0438\u0442\u0435 \u043a \u043e\u0444\u043e\u0440\u043c\u043b\u0435\u043d\u0438\u044e: \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 *\u0434\u043e\u0441\u0442\u0430\u0432\u043a\u0443* \u0438\u043b\u0438 *\u0441\u0430\u043c\u043e\u0432\u044b\u0432\u043e\u0437*\\.\n"
        "5\\. \u041d\u0430\u0436\u043c\u0438\u0442\u0435 *\u041c\u043e\u0438 \u0437\u0430\u043a\u0430\u0437\u044b* \u0434\u043b\u044f \u043f\u0440\u043e\u0441\u043c\u043e\u0442\u0440\u0430 \u0438\u0441\u0442\u043e\u0440\u0438\u0438 \u0437\u0430\u043a\u0430\u0437\u043e\u0432\\.\n\n"
        "\u041f\u043e \u0432\u0441\u0435\u043c \u0432\u043e\u043f\u0440\u043e\u0441\u0430\u043c \u043f\u0438\u0448\u0438\u0442\u0435 /start"
    )

    await update.message.reply_text(help_text, parse_mode="MarkdownV2")


# ---------------------------------------------------------------------------
# Location handler
# ---------------------------------------------------------------------------

async def location_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Save the user location when they share it."""
    if update.message is None or update.message.location is None:
        return

    user = update.effective_user
    if user is None:
        return

    location = update.message.location
    user_locations[user.id] = {
        "latitude": location.latitude,
        "longitude": location.longitude,
    }

    logger.info(
        "User %s (%s) shared location: lat=%s lon=%s",
        user.id,
        user.first_name,
        location.latitude,
        location.longitude,
    )

    await update.message.reply_text(
        "\u2705 \u041c\u0435\u0441\u0442\u043e\u043f\u043e\u043b\u043e\u0436\u0435\u043d\u0438\u0435 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u043e!\n\n"
        "\u0422\u0435\u043f\u0435\u0440\u044c \u0432\u044b \u043c\u043e\u0436\u0435\u0442\u0435 \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u0430\u0442\u0430\u043b\u043e\u0433 \u0438 \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0446\u0432\u0435\u0442\u044b \U0001f490",
        reply_markup=_main_keyboard(),
    )


# ---------------------------------------------------------------------------
# WebApp data handler (order from WebApp)
# ---------------------------------------------------------------------------

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Process data received from the WebApp when the user completes an order."""
    if update.effective_message is None or update.effective_message.web_app_data is None:
        return

    user = update.effective_user
    if user is None:
        return

    raw_data = update.effective_message.web_app_data.data
    logger.info("Received WebApp data from user %s: %s", user.id, raw_data)

    try:
        data = json.loads(raw_data)
    except json.JSONDecodeError:
        logger.error("Failed to parse WebApp data: %s", raw_data)
        await update.effective_message.reply_text(
            "\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0431\u0440\u0430\u0431\u043e\u0442\u043a\u0435 \u0437\u0430\u043a\u0430\u0437\u0430. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u0435\u0449\u0451 \u0440\u0430\u0437."
        )
        return

    items = data.get("items", [])
    delivery_type = data.get("delivery_type", "delivery")
    address = data.get("address")
    location = data.get("location") or user_locations.get(user.id)
    pickup_time = data.get("pickup_time")

    # Build the payload for the order-service (must match OrderCreate schema).
    order_payload = {
        "user_id": user.id,
        "items": items,
        "delivery_type": delivery_type,
        "address": address,
        "pickup_time": pickup_time,
    }

    # Flatten location into latitude/longitude fields.
    if isinstance(location, dict):
        order_payload["latitude"] = location.get("latitude")
        order_payload["longitude"] = location.get("longitude")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{ORDER_SERVICE_URL}/orders",
                json=order_payload,
            )
            response.raise_for_status()
            order = response.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to create order via order-service: %s", exc)
        await update.effective_message.reply_text(
            "\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0437\u0434\u0430\u0442\u044c \u0437\u0430\u043a\u0430\u0437. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
        )
        return

    # Build a user-friendly confirmation message.
    order_id = order.get("id", "N/A")
    total = order.get("total_amount", 0)

    items_text = ""
    for item in items:
        name = item.get("product_name", item.get("name", "\u0422\u043e\u0432\u0430\u0440"))
        qty = item.get("quantity", 1)
        price = item.get("product_price", item.get("price", 0))
        items_text += f"  \u2022 {name} x{qty} \u2014 {price} \u0440\u0443\u0431.\n"

    if delivery_type == "pickup":
        delivery_info = f"\U0001f3ea \u0421\u0430\u043c\u043e\u0432\u044b\u0432\u043e\u0437"
        if pickup_time:
            delivery_info += f" \u043a {pickup_time}"
    else:
        delivery_info = "\U0001f69a \u0414\u043e\u0441\u0442\u0430\u0432\u043a\u0430"
        if address:
            delivery_info += f" \u043f\u043e \u0430\u0434\u0440\u0435\u0441\u0443: {address}"

    confirmation = (
        f"\u2705 \u0417\u0430\u043a\u0430\u0437 #{order_id} \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u0441\u043e\u0437\u0434\u0430\u043d!\n\n"
        f"\U0001f4e6 \u0421\u043e\u0441\u0442\u0430\u0432 \u0437\u0430\u043a\u0430\u0437\u0430:\n{items_text}\n"
        f"\U0001f4b0 \u0418\u0442\u043e\u0433\u043e: {total} \u0440\u0443\u0431.\n"
        f"{delivery_info}\n\n"
        "\u0421\u043f\u0430\u0441\u0438\u0431\u043e \u0437\u0430 \u0437\u0430\u043a\u0430\u0437! \U0001f338"
    )

    await update.effective_message.reply_text(confirmation, reply_markup=_main_keyboard())


# ---------------------------------------------------------------------------
# "My orders" handler
# ---------------------------------------------------------------------------

async def my_orders_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Fetch and display the list of orders for the current user."""
    if update.message is None:
        return

    user = update.effective_user
    if user is None:
        return

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{ORDER_SERVICE_URL}/orders/user/{user.id}",
            )
            response.raise_for_status()
            orders = response.json()
    except httpx.HTTPError as exc:
        logger.error("Failed to fetch orders for user %s: %s", user.id, exc)
        await update.message.reply_text(
            "\u274c \u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0437\u0430\u043a\u0430\u0437\u044b. \u041f\u043e\u043f\u0440\u043e\u0431\u0443\u0439\u0442\u0435 \u043f\u043e\u0437\u0436\u0435."
        )
        return

    if not orders:
        await update.message.reply_text(
            "\U0001f4ed \u0423 \u0432\u0430\u0441 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442 \u0437\u0430\u043a\u0430\u0437\u043e\u0432.\n\n"
            "\u041e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043a\u0430\u0442\u0430\u043b\u043e\u0433, \u0447\u0442\u043e\u0431\u044b \u0432\u044b\u0431\u0440\u0430\u0442\u044c \u0446\u0432\u0435\u0442\u044b! \U0001f490",
            reply_markup=_main_keyboard(),
        )
        return

    text = "\U0001f4e6 *\u0412\u0430\u0448\u0438 \u0437\u0430\u043a\u0430\u0437\u044b:*\n\n"
    for order in orders:
        order_id = order.get("id", "N/A")
        status = order.get("status", "\u043d\u0435\u0438\u0437\u0432\u0435\u0441\u0442\u043d\u043e")
        total = order.get("total_amount", 0)
        delivery_type = order.get("delivery_type", "")
        dtype_label = "\U0001f3ea \u0421\u0430\u043c\u043e\u0432\u044b\u0432\u043e\u0437" if delivery_type == "pickup" else "\U0001f69a \u0414\u043e\u0441\u0442\u0430\u0432\u043a\u0430"
        text += (
            f"\u2022 \u0417\u0430\u043a\u0430\u0437 \\#{order_id}\n"
            f"  \u0421\u0442\u0430\u0442\u0443\u0441: {status}\n"
            f"  {dtype_label}\n"
            f"  \u0418\u0442\u043e\u0433\u043e: {total} \u0440\u0443\u0431\\.\n\n"
        )

    await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=_main_keyboard())
