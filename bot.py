import os
import logging
import traceback
import html
import json
from datetime import datetime

import telegram
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from telegram.constants import ParseMode, ChatAction

import config
import database
import chatgpt


# setup
db = database.Database()
logger = logging.getLogger(__name__)

HELP_MESSAGE = """Commands:
⚪ /retry – сгенерирует ответ заново
⚪ /new - начать новую сессию диалога
⚪ /mode – выбрать режим работы
⚪ /balance – покажет количество потраченных токенов
⚪ /help – помгите вечина

Напишите /mode для выбора режима чат-бота (Поболтать, Кодер, киноэксперт, художник)
----
Owner - @Tipo_4ek
"""

async def register_user_if_not_exists(update: Update, context: CallbackContext, user: User):
    if not db.check_if_user_exists(user.id):
        db.add_new_user(
            user.id,
            update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name= user.last_name
        )


async def start_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.start_new_dialog(user_id)
    
    reply_text = "Ку! Я <b>ChatGPT</b> бот. Юзаю OpenAI API\n\n"
    reply_text += HELP_MESSAGE

    reply_text += "\nСпрашивай!"
    
    await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)


async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    dialog_messages = db.get_dialog_messages(user_id, dialog_id=None)
    if len(dialog_messages) == 0:
        await update.message.reply_text("Нечего повторять :\ 🤷‍♂️")
        return

    last_dialog_message = dialog_messages.pop()
    db.set_dialog_messages(user_id, dialog_messages, dialog_id=None)  # last message was removed from the context

    await message_handle(update, context, message=last_dialog_message["user"], use_new_dialog_timeout=False)


async def message_handle(update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True):
    # check if message is edited
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return
        
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id

    # new dialog timeout
    if use_new_dialog_timeout:
        if (datetime.now() - db.get_user_attribute(user_id, "last_interaction")).seconds > config.new_dialog_timeout:
            db.start_new_dialog(user_id)
            await update.message.reply_text("Начали новую сессию по таймауту ✅")
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    # send typing action
    if (db.get_user_attribute(user_id, "current_chat_mode") == "painter"):
        await update.message.chat.send_action(action="upload_photo")
    else:
        await update.message.chat.send_action(action="typing")

    try:
        message = message or update.message.text
        if (db.get_user_attribute(user_id, "current_chat_mode") != "painter"):
            answer, prompt, n_used_tokens, n_first_dialog_messages_removed = chatgpt.ChatGPT().send_message(
                message,
                dialog_messages=db.get_dialog_messages(user_id, dialog_id=None),
                chat_mode=db.get_user_attribute(user_id, "current_chat_mode"),
            )
        else: # painter
            answer, prompt, n_used_tokens, n_first_dialog_messages_removed, url, urls = chatgpt.ChatGPT().send_photo(
                message,
                dialog_messages=db.get_dialog_messages(user_id, dialog_id=None),
                chat_mode=db.get_user_attribute(user_id, "current_chat_mode"),
            )
        # update user data
        new_dialog_message = {"user": message, "bot": answer, "date": datetime.now()}
        db.set_dialog_messages(
            user_id,
            db.get_dialog_messages(user_id, dialog_id=None) + [new_dialog_message],
            dialog_id=None
        )
        if (n_used_tokens != -1):
            db.set_user_attribute(user_id, "n_used_tokens", n_used_tokens + db.get_user_attribute(user_id, "n_used_tokens"))
        else:
            db.set_user_attribute(user_id, "n_used_tokens", n_used_tokens + db.get_user_attribute(user_id, "n_used_tokens"))

    except Exception as e:
        error_text = f"Чот пошло не так. {e}"
        logger.error(error_text)
        await update.message.reply_text(error_text)
        return

    try:
        if (db.get_user_attribute(user_id, "current_chat_mode") != "painter"):
            await update.message.reply_text(answer, parse_mode=ParseMode.HTML)
        else:
            media_group = []
            for number, url in enumerate(urls):
                media_group.append(InputMediaPhoto(media=url, caption=prompt))
            await update.message.reply_media_group(media_group)

    except telegram.error.BadRequest:
        # answer has invalid characters, so we send it without parse_mode
        await update.message.reply_text(answer)



async def new_dialog_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    db.start_new_dialog(user_id)
    await update.message.reply_text("Начали новый диалог ✅")

    chat_mode = db.get_user_attribute(user_id, "current_chat_mode")
    await update.message.reply_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)


async def show_chat_modes_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    keyboard = []
    for chat_mode, chat_mode_dict in chatgpt.CHAT_MODES.items():
        keyboard.append([InlineKeyboardButton(chat_mode_dict["name"], callback_data=f"set_chat_mode|{chat_mode}")])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("Select chat mode:", reply_markup=reply_markup)


async def set_chat_mode_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    chat_mode = query.data.split("|")[1].split(' ')[0]
    db.set_user_attribute(user_id, "current_chat_mode", chat_mode)
    db.start_new_dialog(user_id)

    await query.edit_message_text(
        f"<b>{chatgpt.CHAT_MODES[chat_mode]['name']}</b> Чат мод поставлен",
        parse_mode=ParseMode.HTML
    )

    await query.edit_message_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)


async def show_balance_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)

    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    n_used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    n_spent_dollars = n_used_tokens * (0.02 / 1000)
    text = f"Всего на один api key бесплатно выделено $18/3мес. <code>Картинка 1024х1024 весит $0.02</code>.\nДля текста (примерно):\n<code>1 токен - 4 латинских символа</code>\n<code>30 токенов - 1-2 предложения</code>\n<code>100 токенов - 75 букв</code>\n<b>В боте предусмотрена полуавтоматическая (командой в бота) ротация токена, в случае, если токен протух/кончилась квота.</b>\n\n"
    text += f"Потрачено <b>{n_spent_dollars:.03f}$ (не считаются изображения)</b>\n" 
    text += f"Потрачено <b>{n_used_tokens}</b> токенов <i>(Стоимость: $0.02/1000 токенов).</i>\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def rotate_api_token_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.message.from_user.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    n_used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    token_index = chatgpt.rotate_token()
    text = f"Ротация токена успешно произведена. Текущий токен - {token_index}\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def edited_message_handle(update: Update, context: CallbackContext):
    text = "🥲Редактирование сообщений <b>пока что </b> Не поддержано"
    await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)


async def error_handle(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # collect error message
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)[:2000]
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"An exception was raised while handling an update. Траблы с монгой?\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(update.effective_chat.id, message, parse_mode=ParseMode.HTML)


def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .build()
    )
    chatgpt.init_api_key()

    # add handlers
    if len(config.allowed_telegram_usernames) == 0:
        user_filter = filters.ALL
    else:
        user_filter = filters.User(username=config.allowed_telegram_usernames)

    application.add_handler(CommandHandler("start", start_handle, filters=user_filter))
    application.add_handler(CommandHandler("help", help_handle, filters=user_filter))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle))
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(CommandHandler("new", new_dialog_handle, filters=user_filter))
    
    application.add_handler(CommandHandler("mode", show_chat_modes_handle, filters=user_filter))
    application.add_handler(CallbackQueryHandler(set_chat_mode_handle, pattern="^set_chat_mode"))

    application.add_handler(CommandHandler("balance", show_balance_handle, filters=user_filter))
    application.add_handler(CommandHandler("rotate", rotate_api_token_handle, filters=user_filter))
    
    application.add_error_handler(error_handle)
    
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
