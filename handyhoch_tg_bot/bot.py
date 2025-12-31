import logging
from typing import List, Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .config import Settings, load_settings
from .data_loader import Listing, load_listings, shortlist
from .search import filter_listings, format_listing

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

CATEGORY, PROVIDER_TYPE, SCAM_FILTER, AGE, BUDGET, DISTRICTS, ROOMS = range(7)
WG = "wg"
WOHNUNG = "wohnung"
HOUSING = "housing_association"
PRIVATE = "private"


def _require_listings(context: ContextTypes.DEFAULT_TYPE) -> List[Listing]:
    listings: Optional[List[Listing]] = context.bot_data.get("listings")
    if listings is None:
        raise RuntimeError("Listings are not loaded.")
    return listings


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я помогу найти квартиры в Берлине. "
        "Команды: /search чтобы подобрать варианты, /listings чтобы увидеть топ предложений, /help для справки."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Доступные команды:\n"
        "• /search — пошаговый подбор по типу (WG/Wohnung), типу арендодателя (баугезельшафт/частник), периоду публикации, бюджету, районам и комнатам.\n"
        "• /listings — покажет несколько свежих вариантов без фильтров.\n"
        "• /cancel — выйти из сценария поиска.\n\n"
        "Перед запуском установите переменные окружения BOT_TOKEN и LISTINGS_PATH (опционально)."
    )


async def show_listings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    listings = _require_listings(context)
    top = shortlist(listings)
    if not top:
        await update.message.reply_text("Пока нет доступных квартир — загрузите данные и попробуйте снова.")
        return

    await update.message.reply_text(
        "\n\n".join(format_listing(listing) for listing in top), disable_web_page_preview=True
    )


async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["filters"] = {"max_age_hours": 5.0}
    await update.message.reply_text(
        "Что ищем? Введите 'WG' или 'Wohnung'."
    )
    return CATEGORY


async def category_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    mapping = {
        "wg": WG,
        "вг": WG,
        "комната": WG,
        "wohngemeinschaft": WG,
        "wohnung": WOHNUNG,
        "квартира": WOHNUNG,
        "flat": WOHNUNG,
    }
    if text not in mapping:
        await update.message.reply_text("Укажите 'WG' или 'Wohnung'.")
        return CATEGORY

    context.user_data["filters"] = {"category": mapping[text]}
    await update.message.reply_text(
        "Кто сдает? Напишите 'bau' для Wohnbaugesellschaft или 'privat' для частников."
    )
    return PROVIDER_TYPE


async def provider_type_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    filters_data = context.user_data.get("filters", {})

    if text in {"bau", "housing", "gesellschaft", "baugesellschaft"}:
        filters_data["provider_type"] = HOUSING
    elif text in {"privat", "private"}:
        filters_data["provider_type"] = PRIVATE
    else:
        await update.message.reply_text("Укажите 'bau' (баугезельшафт) или 'privat' (частник).")
        return PROVIDER_TYPE

    context.user_data["filters"] = filters_data
    await update.message.reply_text(
        "Фильтровать подозрительные объявления? Напишите 'да' или 'нет'."
    )
    return SCAM_FILTER


async def scam_filter_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    filters_data = context.user_data.get("filters", {})

    if text in {"да", "yes", "y"}:
        filters_data["exclude_suspected_scam"] = True
    elif text in {"нет", "no", "n"}:
        filters_data["exclude_suspected_scam"] = False
    else:
        await update.message.reply_text("Ответьте 'да' или 'нет'.")
        return SCAM_FILTER

    context.user_data["filters"] = filters_data
    await update.message.reply_text(
        "За какой период показывать свежие объявления? Формат: '5h' или '2d'. По умолчанию 5h. Напишите число с суффиксом или 'skip'."
    )
    return AGE


def _parse_age_input(text: str) -> Optional[float]:
    t = text.strip().lower()
    if not t:
        return None
    if t.isdigit():
        return float(t)
    if t.endswith("h") and t[:-1].replace(".", "", 1).isdigit():
        return float(t[:-1])
    if t.endswith("d") and t[:-1].replace(".", "", 1).isdigit():
        return float(t[:-1]) * 24
    return None


async def age_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    filters_data = context.user_data.get("filters", {})

    if text not in {"skip", "пропустить"}:
        parsed = _parse_age_input(text)
        if parsed is None:
            await update.message.reply_text("Укажите число с суффиксом h (часы) или d (дни), например 5h или 2d, либо 'skip'.")
            return AGE
        filters_data["max_age_hours"] = parsed

    context.user_data["filters"] = filters_data
    await update.message.reply_text(
        "Максимальная арендная плата в евро? Напишите число или 'skip', чтобы пропустить."
    )
    return BUDGET


async def budget_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    filters_data = context.user_data.get("filters", {})

    if text != "skip" and text != "пропустить":
        try:
            filters_data["max_rent"] = int(text)
        except ValueError:
            await update.message.reply_text("Пожалуйста, укажите число или 'skip'. Попробуем еще раз.")
            return BUDGET

    context.user_data["filters"] = filters_data
    await update.message.reply_text(
        "Какие районы Берлина интересуют? Укажите через запятую или напишите 'skip'."
    )
    return DISTRICTS


async def districts_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    filters_data = context.user_data.get("filters", {})

    if text.lower() not in {"skip", "пропустить"}:
        districts = [part.strip() for part in text.split(",") if part.strip()]
        filters_data["districts"] = districts

    context.user_data["filters"] = filters_data
    await update.message.reply_text(
        "Минимальное число комнат? Укажите число или 'skip'."
    )
    return ROOMS


async def rooms_step(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip().lower()
    filters_data = context.user_data.get("filters", {})

    if text not in {"skip", "пропустить"}:
        try:
            filters_data["min_rooms"] = int(text)
        except ValueError:
            await update.message.reply_text("Введите число или 'skip'.")
            return ROOMS

    context.user_data["filters"] = filters_data
    return await _finish_search(update, context)


async def _finish_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    listings = _require_listings(context)
    filters_data = context.user_data.get("filters", {})
    matches = filter_listings(listings, **filters_data)
    top_matches = shortlist(matches, limit=8)

    if not top_matches:
        await update.message.reply_text(
            "По вашим условиям пока ничего не найдено. Попробуйте другие фильтры."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "Нашла следующие варианты:\n\n"
        + "\n\n".join(format_listing(item) for item in top_matches),
        disable_web_page_preview=True,
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Поиск остановлен. Можно запустить заново командой /search.")
    return ConversationHandler.END


def build_application(settings: Optional[Settings] = None) -> Application:
    settings = settings or load_settings()
    listings = load_listings(settings.listings_path)

    application = Application.builder().token(settings.bot_token).build()
    application.bot_data["listings"] = listings

    conversation = ConversationHandler(
        entry_points=[CommandHandler("search", start_search)],
        states={
            CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, category_step)],
            PROVIDER_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, provider_type_step)],
            SCAM_FILTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, scam_filter_step)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_step)],
            BUDGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget_step)],
            DISTRICTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, districts_step)],
            ROOMS: [MessageHandler(filters.TEXT & ~filters.COMMAND, rooms_step)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("listings", show_listings))
    application.add_handler(conversation)
    application.add_handler(CommandHandler("cancel", cancel))

    return application


def main() -> None:
    settings = load_settings()
    application = build_application(settings)
    logger.info("Bot started with listings from %s", settings.listings_path)
    application.run_polling()


if __name__ == "__main__":
    main()
