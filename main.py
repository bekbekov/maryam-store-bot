import json
import os
import logging

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

# ========== SETTINGS ==========

TOKEN = (
    os.getenv("BOT_TOKEN")
    or os.getenv("TELEGRAM_BOT_TOKEN")
    or os.getenv("TELEGRAM_TOKEN")
    or os.getenv("TOKEN")
)
ADMIN_ID = 792922890

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ========== PRODUCTS ==========

def load_products():
    try:
        with open("products.json", "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        logging.exception("Cannot load products.json")
        return {"categories": []}


def main_menu():
    keyboard = [
        [InlineKeyboardButton("👜 Сумки", callback_data="cat_bags")],
        [InlineKeyboardButton("⌚ Часы", callback_data="cat_watches")],
        [InlineKeyboardButton("🖼 Картина", callback_data="cat_art")],
        [InlineKeyboardButton("📞 Связаться с продавцом", callback_data="contact")]
    ]
    return InlineKeyboardMarkup(keyboard)


# ========== START ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Добро пожаловать в Maryam Store! 🛍\n\n"
        "Здесь вы можете посмотреть товары, "
        "узнать цены и оформить заказ.\n\n"
        "Выберите категорию:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu()
    )


# ========== CATEGORIES ==========

async def category_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    category_id = query.data.replace("cat_", "")
    data = load_products()

    category = next(
        (
            item for item in data["categories"]
            if item["id"] == category_id
        ),
        None
    )

    if not category:
        await query.message.reply_text("Категория не найдена.")
        return

    products = category.get("products", [])

    if not products:
        await query.message.reply_text(
            "Пока товары в этой категории не добавлены.",
            reply_markup=main_menu()
        )
        return

    for product in products:
        keyboard = [[
            InlineKeyboardButton(
                "🛒 Заказать",
                callback_data=f"order_{product['id']}"
            )
        ]]

        caption = (
            f"**{product['name']}**\n\n"
            f"{product['description']}\n\n"
            f"Цена: {product['price']} ₸"
        )

        await query.message.reply_photo(
            photo=product["photo"],
            caption=caption,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ========== ORDER ==========

async def order_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    product_id = query.data.replace("order_", "")
    data = load_products()

    product = None

    for category in data["categories"]:
        for item in category.get("products", []):
            if str(item["id"]) == product_id:
                product = item
                break

    if not product:
        await query.message.reply_text("Товар не найден.")
        return

    context.user_data["pending_order"] = product_id

    await query.message.reply_text(
        f"Вы выбрали: {product['name']}\n\n"
        "Напишите, пожалуйста, ваше имя и контакт для связи."
    )


# ========== CUSTOMER MESSAGE ==========

async def customer_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    product_id = context.user_data.get("pending_order")

    if not product_id:
        await update.message.reply_text(
            "Пожалуйста, выберите товар в каталоге.",
            reply_markup=main_menu()
        )
        return

    data = load_products()
    product = None

    for category in data["categories"]:
        for item in category.get("products", []):
            if str(item["id"]) == product_id:
                product = item
                break

    user = update.effective_user

    username = (
        f"@{user.username}"
        if user.username else "Не указан"
    )

    if product:
        order_text = (
            "🛍 НОВАЯ ЗАЯВКА\n\n"
            f"Товар: {product['name']}\n"
            f"Цена: {product['price']} ₸\n\n"
            f"Покупатель: {user.full_name}\n"
            f"Username: {username}\n"
            f"Telegram ID: {user.id}\n\n"
            f"Контакт покупателя:\n{update.message.text}"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=order_text
            )

            await update.message.reply_text(
                "Спасибо! Ваша заявка отправлена продавцу. 😊",
                reply_markup=main_menu()
            )

        except Exception:
            logging.exception("Order notification failed")
            await update.message.reply_text(
                "Не удалось отправить заявку. Попробуйте позже."
            )

    context.user_data.pop("pending_order", None)


# ========== CONTACT ==========

async def contact_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Для связи с продавцом отправьте сообщение через этот чат."
    )


# ========== MAIN ==========

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(
        CallbackQueryHandler(
            category_handler,
            pattern="^cat_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            order_handler,
            pattern="^order_"
        )
    )

    app.add_handler(
        CallbackQueryHandler(
            contact_handler,
            pattern="^contact$"
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            customer_message
        )
    )

    print("Maryam Store bot is running...")

    app.run_polling()


if __name__ == "__main__":
    main()
