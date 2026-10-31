

import os
import json
import logging
import uuid

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

# Пока администратор — твой аккаунт
ADMIN_IDS = {792922890}

PRODUCTS_FILE = "products.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

CATEGORIES = {
    "bags": "👜 Сумки",
    "watches": "⌚ Часы",
    "art": "🖼 Картина"
}


# ========== DATABASE ==========

def load_products():
    try:
        with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {"categories": [
            {"id": key, "name": value, "products": []}
            for key, value in CATEGORIES.items()
        ]}


def save_products(data):
    temp_file = PRODUCTS_FILE + ".tmp"

    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    os.replace(temp_file, PRODUCTS_FILE)


def is_admin(user_id):
    return user_id in ADMIN_IDS


def find_product(product_id):
    data = load_products()

    for category in data["categories"]:
        for product in category.get("products", []):
            if str(product["id"]) == str(product_id):
                return category, product

    return None, None


# ========== KEYBOARDS ==========

def main_menu():
    keyboard = [
        [InlineKeyboardButton("👜 Сумки", callback_data="cat_bags")],
        [InlineKeyboardButton("⌚ Часы", callback_data="cat_watches")],
        [InlineKeyboardButton("🖼 Картина", callback_data="cat_art")],
        [
            InlineKeyboardButton(
                "📞 Связаться с продавцом",
                url="https://t.me/+77757711007"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def admin_menu():
    keyboard = [
        [InlineKeyboardButton("➕ Добавить товар", callback_data="admin_add")],
        [InlineKeyboardButton("📦 Все товары", callback_data="admin_list")],
        [InlineKeyboardButton("⬅️ Главное меню", callback_data="admin_home")]
    ]

    return InlineKeyboardMarkup(keyboard)


def category_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                name,
                callback_data=f"addcat_{key}"
            )
        ]
        for key, name in CATEGORIES.items()
    ])


# ========== START ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()

    await update.message.reply_text(
        "Добро пожаловать в Maryam Store! 🛍\n\n"
        "Выберите категорию товаров:",
        reply_markup=main_menu()
    )


# ========== ADMIN PANEL ==========

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Нет доступа.")
        return

    context.user_data.clear()

    await update.message.reply_text(
        "⚙️ Панель управления Maryam Store",
        reply_markup=admin_menu()
    )


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update.effective_user.id):
        await query.message.reply_text("Нет доступа.")
        return

    action = query.data

    if action == "admin_home":
        context.user_data.clear()
        await query.message.reply_text(
            "Главное меню магазина:",
            reply_markup=main_menu()
        )

    elif action == "admin_add":
        context.user_data.clear()
        context.user_data["state"] = "choose_category"

        await query.message.reply_text(
            "Выберите категорию нового товара:",
            reply_markup=category_keyboard()
        )

    elif action == "admin_list":
        data = load_products()
        lines = ["📦 Товары магазина:\n"]

        keyboard = []

        for category in data["categories"]:
            for product in category.get("products", []):
                status = (
                    "Продан"
                    if product.get("sold", False)
                    else "В продаже"
                )

                lines.append(
                    f"{product['name']} — "
                    f"{product['price']} ₸ — {status}"
                )

                keyboard.append([
                    InlineKeyboardButton(
                        f"❌ Продать/снять: {product['name']}",
                        callback_data=f"admin_sold_{product['id']}"
                    ),
                    InlineKeyboardButton(
                        "🗑 Удалить",
                        callback_data=f"admin_delete_{product['id']}"
                    )
                ])

        keyboard.append([
            InlineKeyboardButton(
                "⬅️ Назад",
                callback_data="admin_back"
            )
        ])

        await query.message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif action == "admin_back":
        await query.message.reply_text(
            "Панель управления:",
            reply_markup=admin_menu()
        )

    elif action.startswith("addcat_"):
        category_id = action.replace("addcat_", "")

        if category_id not in CATEGORIES:
            return

        context.user_data["new_product"] = {
            "category": category_id
        }

        context.user_data["state"] = "name"

        await query.message.reply_text(
            "Введите название товара:"
        )

    elif action.startswith("admin_sold_"):
        product_id = action.replace("admin_sold_", "")
        category, product = find_product(product_id)

        if product:
            data = load_products()

            for cat in data["categories"]:
                for item in cat.get("products", []):
                    if str(item["id"]) == product_id:
                        item["sold"] = not item.get("sold", False)

            save_products(data)

            await query.message.reply_text(
                "Статус товара обновлён."
            )

    elif action.startswith("admin_delete_"):
        product_id = action.replace("admin_delete_", "")
        data = load_products()

        for category in data["categories"]:
            category["products"] = [
                p for p in category.get("products", [])
                if str(p["id"]) != product_id
            ]

        save_products(data)

        await query.message.reply_text(
            "Товар удалён из каталога."
        )


# ========== ADD PRODUCT FLOW ==========

async def admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if not is_admin(user_id):
        return

    state = context.user_data.get("state")

    if not state:
        return

    new_product = context.user_data.get("new_product", {})

    if state == "name":
        new_product["name"] = update.message.text.strip()
        context.user_data["state"] = "description"

        await update.message.reply_text(
            "Введите описание товара:"
        )

    elif state == "description":
        new_product["description"] = update.message.text.strip()
        context.user_data["state"] = "price"

        await update.message.reply_text(
            "Введите цену в тенге (только число):"
        )

    elif state == "price":
        try:
            price = int(update.message.text.strip())

            if price < 0:
                raise ValueError

        except ValueError:
            await update.message.reply_text(
                "Введите корректную цену числом."
            )
            return

        new_product["price"] = price
        context.user_data["state"] = "photo"

        await update.message.reply_text(
            "Теперь отправьте одну фотографию товара.\n"
            "Если фотографии пока нет, напишите: пропустить"
        )

    elif state == "photo":
        photo_id = ""

        if update.message.photo:
            photo_id = update.message.photo[-1].file_id

        elif update.message.text and update.message.text.lower() == "пропустить":
            photo_id = ""

        else:
            await update.message.reply_text(
                "Отправьте фотографию или напишите «пропустить»."
            )
            return

        new_product["photo"] = photo_id
        new_product["id"] = str(uuid.uuid4())[:8]
        new_product["sold"] = False

        data = load_products()

        for category in data["categories"]:
            if category["id"] == new_product["category"]:
                category.setdefault("products", []).append(new_product)
                break

        save_products(data)

        context.user_data.clear()

        await update.message.reply_text(
            "✅ Товар добавлен в каталог!",
            reply_markup=admin_menu()
        )


# ========== CUSTOMER CATALOG ==========

async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        return

    products = [
        p for p in category.get("products", [])
        if not p.get("sold", False)
    ]

    if not products:
        await query.message.reply_text(
            "В этой категории пока нет доступных товаров.",
            reply_markup=main_menu()
        )
        return

    for product in products:
        caption = (
            f"<b>{product['name']}</b>\n\n"
            f"{product['description']}\n\n"
            f"Цена: {product['price']} ₸"
        )

        keyboard = [[
            InlineKeyboardButton(
                "🛒 Заказать",
                callback_data=f"order_{product['id']}"
            )
        ]]

        markup = InlineKeyboardMarkup(keyboard)

        if product.get("photo"):
            await query.message.reply_photo(
                photo=product["photo"],
                caption=caption,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            await query.message.reply_text(
                caption,
                parse_mode="HTML",
                reply_markup=markup
            )


# ========== ORDERS ==========

async def order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    product_id = query.data.replace("order_", "")
    category, product = find_product(product_id)

    if not product or product.get("sold", False):
        await query.message.reply_text(
            "К сожалению, товар уже недоступен."
        )
        return

    context.user_data["pending_order"] = product_id

    await query.message.reply_text(
        "Для оформления заявки напишите ваше имя "
        "и контактный номер телефона одним сообщением."
    )


async def customer_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get("pending_order")

    if not product_id:
        return

    category, product = find_product(product_id)

    if not product:
        context.user_data.pop("pending_order", None)
        await update.message.reply_text("Товар больше не найден.")
        return

    user = update.effective_user

    order_text = (
        "🛍 НОВАЯ ЗАЯВКА\n\n"
        f"Товар: {product['name']}\n"
        f"Цена: {product['price']} ₸\n\n"
        f"Покупатель: {user.full_name}\n"
        f"Username: @{user.username if user.username else 'не указан'}\n"
        f"Telegram ID: {user.id}\n\n"
        f"Контакт покупателя:\n{update.message.text}"
    )

    sent = False

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=order_text
            )
            sent = True
        except Exception:
            logging.exception("Could not send order to admin %s", admin_id)

    if sent:
        await update.message.reply_text(
            "Спасибо! Ваша заявка отправлена продавцу. 😊",
            reply_markup=main_menu()
        )
    else:
        await update.message.reply_text(
            "Не удалось отправить заявку. Попробуйте связаться с продавцом напрямую."
        )

    context.user_data.pop("pending_order", None)


# ========== CONTACT ==========

async def contact_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "Связаться с продавцом можно напрямую:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "📞 Написать продавцу",
                    url="https://t.me/+77757711007"
                )
            ]
        ])
    )


# ========== MAIN ==========

def main():
    if not TOKEN:
        raise RuntimeError("BOT_TOKEN is not configured!")

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_command))

    app.add_handler(
        CallbackQueryHandler(
            admin_handler,
            pattern="^(admin_|addcat_)"
        )
    )

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
            filters.PHOTO | filters.TEXT & ~filters.COMMAND,
            admin_message
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            customer_message
        )
    )

    logging.info("Maryam Store bot is starting...")

    app.run_polling()


if __name__ == "__main__":
    main()
