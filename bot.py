'''
-------------------------------------------
  Copyright (c) 2023 Tipo-4ek
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.
  
'''

import os
import logging
import traceback
import html
import asyncio
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
    AIORateLimiter,
    filters
)
from telegram.constants import ParseMode, ChatAction

import config
import database
import chatgpt

semaphores_per_users = {}
user_tasks = {}


# setup
db = database.Database()
logger = logging.getLogger(__name__)

HELP_MESSAGE = """Commands:
⚪ /mode – Выбрать режим работы бота
⚪ /new – Начать новую сессию диалога (Если хотите забыть текущий контекст)
⚪ /balance – Показать количество потраченных токенов. Только для статистики
⚪ /dialogs – Показать прошлые диалоги и переключиться на один из них
⚪ /help – помгите вечина

Напишите /mode для выбора режима чат-бота (Ассистент, кодер, киноэксперт, художник)
----
Owner – @Tipo_4ek
"""
async def check_required_subscriptions(update: Update, context: CallbackContext, user: User):
    
    user_id = user.id
    required_chat_ids_to_subcribe = []
    # Обходим все элементы в словаре REQUIRED_CHATS_TO_SUBSCRIBE
    for key in config.REQUIRED_CHATS_TO_SUBSCRIBE:
        # Добавляем значение "id" каждого элемента в список
        required_chat_ids_to_subcribe.append(config.REQUIRED_CHATS_TO_SUBSCRIBE[key]["id"])

    need_to_subscribe = False
    for chat_id in required_chat_ids_to_subcribe:
        user_subscribe_status = (await context.bot.get_chat_member(chat_id,user_id)).status
        if user_subscribe_status in ["creator", "member"]:
            with open("log.log", "a") as log_file:
                    log_file.write(f"\nsubscribe --> subscription to {user_id} is OK")
        else:
            need_to_subscribe = True

    if (need_to_subscribe == False):
        return False
    else:
        with open("log.log", "a") as log_file:
                    log_file.write(f"\nsubscribe --> send subscribe action to {user_id}")
        keyboard = []
        for chat_id in required_chat_ids_to_subcribe:
            for key in config.REQUIRED_CHATS_TO_SUBSCRIBE:
                if config.REQUIRED_CHATS_TO_SUBSCRIBE[key]['id'] == chat_id:
                    keyboard.append([InlineKeyboardButton(config.REQUIRED_CHATS_TO_SUBSCRIBE[key]["name"], url=config.REQUIRED_CHATS_TO_SUBSCRIBE[key]["link"])])
        keyboard.append([InlineKeyboardButton("Я подписался✅", callback_data=f"i_am_subscribe")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        try:
            await update.message.reply_text("Please subscribe to these channels:", reply_markup=reply_markup)
        except:
                #await update.message.reply_text("Please subscribe to these channels:", reply_markup=reply_markup)
                await context.bot.send_message(chat_id=user_id, text="Please subscribe to these channels:", reply_markup=reply_markup)
        return True
    
async def check_i_am_subscribe_action(update: Update, context: CallbackContext, mode = "callback"):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)

    query = update.callback_query
    await query.answer()
    if await check_required_subscriptions(update, context, update.callback_query.from_user): return
    await query.edit_message_text(f"Проверка на подписки выполнена.")
    await start_handle(update, context)


async def register_user_if_not_exists(update: Update, context: CallbackContext, user: User):
    if not db.check_if_user_exists(user.id):
        db.add_new_user(
            user.id,
            update.message.chat_id,
            username=user.username,
            first_name=user.first_name,
            last_name= user.last_name
        )

    if user.id not in semaphores_per_users:
        semaphores_per_users[user.id] = asyncio.Semaphore(1)


async def start_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.effective_chat)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    user_id = update.effective_chat.id
    
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    db.start_new_dialog(user_id)
    
    reply_text = "Ку! Я <b>ChatGPT</b> бот. Юзаю OpenAI API\n\n"
    reply_text += HELP_MESSAGE

    reply_text += "\n<b>По умолчанию выставлен мод Ассистента</b>. Он НЕ УМЕЕТ создавать картинки. У каждого режима чат-бота своя роль. Если хотите изменить режим ответов - используйте /mode.\n\n------\nP.S. Буду рад, если ты поставишь Звездочку на <a href='https://github.com/Tipo-4ek/tipo_chatgpt_bot'>Github</a>"
    #await update.message.reply_text(reply_text, parse_mode=ParseMode.HTML)
    await context.bot.send_message(chat_id=user_id, text=reply_text, parse_mode=ParseMode.HTML)
    await show_chat_modes_handle(update, context)


async def help_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    if await is_previous_message_not_answered_yet(update, context): return
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    if await is_previous_message_not_answered_yet(update, context): return
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    dialog_messages = db.get_dialog_messages(user_id, dialog_id=None)
    if len(dialog_messages) == 0:
        await update.message.reply_text("Нечего повторять :\ 🤷‍♂️")
        return

    last_dialog_message = dialog_messages.pop()
    db.set_dialog_messages(user_id, dialog_messages, dialog_id=None)  # last message was removed from the context
    await message_handle(update, context, message=last_dialog_message["user"], use_new_dialog_timeout=False)


async def message_handle(update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True):
    user_id = update.effective_chat.id
    if await check_required_subscriptions(update, context, update.effective_chat): return
    if await is_previous_message_not_answered_yet(update, context): return
    # check if message is edited
    if update.edited_message is not None:
        await edited_message_handle(update, context)
        return
        
    await register_user_if_not_exists(update, context, update.message.from_user)

    if user_id not in semaphores_per_users:
        semaphores_per_users[user.id] = asyncio.Semaphore(1)
    
    async def message_handle_fn(message=None):
        parse_mode = {
                    "HTML": ParseMode.HTML,
                    "markdown": ParseMode.MARKDOWN,
                    "MARKDOWN_V2": ParseMode.MARKDOWN_V2
                }[chatgpt.CHAT_MODES[db.get_user_attribute(user_id, "current_chat_mode")]['parse_mode']]


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
                answer, prompt, n_used_tokens, n_first_dialog_messages_removed = await chatgpt.ChatGPT().send_message(
                    message,
                    dialog_messages=db.get_dialog_messages(user_id, dialog_id=None),
                    chat_mode=db.get_user_attribute(user_id, "current_chat_mode"),
                )
            else: # painter
                answer, prompt, n_used_tokens, n_first_dialog_messages_removed, first_url, urls = await chatgpt.ChatGPT().send_photo(
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
            if "is not subscriptable" in str(e):
                error_text = "Где-то правили базу. Напиши /start еще раз, пожалуйста"
            else:
                error_text = f"Чот пошло не так. {e}"
            logger.error(error_text)
            await update.message.reply_text(error_text)
            return
        except asyncio.CancelledError:
            # await update.message.reply_text("Сорри, но openai не вернула ответ на запрос")
            raise

        try:
            if (db.get_user_attribute(user_id, "current_chat_mode") != "painter"):
                # got "answer"
                user_parse_mode = chatgpt.CHAT_MODES[db.get_user_attribute(user_id, "current_chat_mode")]['parse_mode']
                if (user_parse_mode in ["markdown", "MARKDOWN_V2"]):
                    if len(answer) > 4096: # This does not guarantee that the final markdown markup will be < 4096 characters. The condition only allows you to try to send short messages in text, just long ones in a file. If the short message turns out to be rich markup, then exception handle will work
                        file_to_upload = open(str(user_id)+".txt", "w+")
                        file_to_upload.write(answer)
                        file_to_upload.close()
                        file_to_upload = open(str(user_id)+".txt", "rb")
                        await update.message.reply_text("Сообщение оказалось слишком длинным, я отправлю его файлом. Иногда chatGPT отправляет сообщение не полностью. Если такое случилось - напиши continue и придет следующая часть ответа")
                        await update.message.reply_document(file_to_upload)
                        file_to_upload.close()
                    else:
                        await update.message.reply_text(answer, parse_mode=parse_mode)
                else:
                    if len(answer) > 4096:
                        for x in range(0, len(answer), 4096):
                            await update.message.reply_text(answer[x:x+4096], parse_mode=parse_mode)
                    else:
                        await update.message.reply_text(answer, parse_mode=parse_mode)
                
                # await update.message.reply_text(answer, parse_mode=chatgpt.CHAT_MODES[db.get_user_attribute(user_id, "current_chat_mode")]['parse_mode'])
            else:
                media_group = []
                with open("log.log", "a") as log_file:
                    log_file.write(f"\ndebug --> Пришел list urls ==== {urls}")
                for number, url in enumerate(urls):
                    media_group.append(InputMediaPhoto(media=url, caption=prompt))
                await update.message.reply_media_group(media_group)

        except telegram.error.BadRequest as e:
            curr_parse_mode = chatgpt.CHAT_MODES[db.get_user_attribute(user_id, "current_chat_mode")]['parse_mode']
            for x in range(0, len(answer), 4096):
                await update.message.reply_text(answer[x:x+4096])

            
            await update.message.reply_text("Иногда chatgpt api возвращает не весь ответ... Проблема не на нашей стороне. Если такое случилось - напишите continue")
            
        except Exception as e:
            await update.message.reply_text(f"Телеге плохо. Api вернула ошибку {e}")
            with open("log.log", "a") as log_file:
                    log_file.write(f"\ndebug --> Не удалось отправить картинку: {e}")

    async with semaphores_per_users[user_id]:
        task = asyncio.create_task(message_handle_fn())
        user_tasks[user_id] = task
    
        try:
            await task
        except asyncio.CancelledError:
            await update.message.reply_text("Запрос отменен. Скорее всего api телеграмма не работает.", parse_mode=ParseMode.HTML)
        finally:
            if user_id in user_tasks:
                del user_tasks[user_id]
        



async def new_dialog_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    if await is_previous_message_not_answered_yet(update, context): return

    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    db.start_new_dialog(user_id)
    await update.message.reply_text("Начали новый диалог ✅")

    chat_mode = db.get_user_attribute(user_id, "current_chat_mode")
    await update.message.reply_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)


async def admin_handle(update: Update, context: CallbackContext):
    # secret stat
    pass
    

async def show_chat_modes_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.effective_chat)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    keyboard = []
    for chat_mode, chat_mode_dict in chatgpt.CHAT_MODES.items():
        keyboard.append([InlineKeyboardButton(chat_mode_dict["name"], callback_data=f"set_chat_mode|{chat_mode}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=user_id, text="Select chat mode:", reply_markup=reply_markup)
    #await update.message.reply_text("Select chat mode:", reply_markup=reply_markup)


async def show_dialogs_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.effective_chat)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    user_id = update.effective_chat.id
    keyboard = []

    dialogs = db.get_dialogs(user_id = user_id)
    json_list = json.loads(dialogs)
    for d in json_list:
        if (d["messages"]):
            dialog_start_time = d["start_time"][:16]
            dialog_shortcut = dialog_start_time + " " + d["messages"][0]["user"][:50]
            dialog_id = d["_id"]
            keyboard.append([InlineKeyboardButton(dialog_shortcut, callback_data=f"set_dialog_id|{dialog_id}")])
    reply_markup = InlineKeyboardMarkup(keyboard[:10])
    if (keyboard != []):
        await context.bot.send_message(chat_id=user_id, text="↓ Select your dialog:", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=user_id, text="No dialogs found. Maybe you wanted to start a /new dialog?")

async def set_chat_mode_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    chat_mode = query.data.split("|")[1].split(' ')[0]
    with open("log.log", "a") as log_file:
                log_file.write(f"\ndebug --> Set mode to {update.callback_query.from_user.username} > {chat_mode}")
    db.set_user_attribute(user_id, "current_chat_mode", chat_mode)
    db.start_new_dialog(user_id)

    await query.edit_message_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)

async def set_dialog_id_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    dialog_id = query.data.split("|")[1].split(' ')[0]
    with open("log.log", "a") as log_file:
                log_file.write(f"\ndebug --> /dialog CHANGED to {update.callback_query.from_user.username} > {dialog_id}")
    db.set_user_attribute(user_id, "current_dialog_id", dialog_id)

    await query.edit_message_text(f"Контекст диалога успешно изменен")


async def show_balance_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return

    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    n_used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    n_spent_dollars = n_used_tokens * (0.002 / 1000)
    text = f"Всего на один api key бесплатно выделено $18/3мес.\n<code>Картинка 1024х1024 весит $0.02</code>.\n<code>Текст $0.002/1000 токенов.</code>\n\nМатематика приблизительно такая:\n<code>1 токен - 4 латинских символа</code>\n<code>30 токенов - 1-2 предложения</code>\n<code>100 токенов - 75 букв</code>\nВ боте предусмотрена полуавтоматическая (командой в бота) ротация токена, в случае, если токен протух/кончилась квота.\n\n"
    text += f"Потрачено денег <b>${n_spent_dollars:.03f}</b>(текст + изображения)\n" 
    text += f"Потрачено токенов <b>{n_used_tokens}</b> токенов <i>.</i>\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def rotate_api_token_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    n_used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    token_index = chatgpt.rotate_token()
    text = f"Ротация токена успешно произведена. Текущий токен - {token_index}\n"
    await context.bot.send_message(chat_id=268122930, text=f"TOKEN ROTATED by {user_id}.\nТекущий токен - {token_index}\nCHECK BOT CONDITION")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def edited_message_handle(update: Update, context: CallbackContext):
    text = "🥲Редактирование сообщений <b>пока что </b> Не поддержано"
    await update.edited_message.reply_text(text, parse_mode=ParseMode.HTML)
    

async def is_previous_message_not_answered_yet(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return

    user_id = update.effective_chat.id
    if semaphores_per_users[user_id].locked():
        text = "Подожди ответа на предыдущее сообщение и напиши вопрос еще раз."
        await update.message.reply_text(text, reply_to_message_id=update.message.id, parse_mode=ParseMode.HTML)
        return True
    else:
        return False

async def error_handle(update: Update, context: CallbackContext) -> None:
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # collect error message
    tb_list = traceback.format_exception(None, context.error)
    tb_string = "".join(tb_list)[:2000]
    update_str = update.to_dict() if isinstance(update, Update) else str(update)
    message = (
        f"Необработанное Исключение!\n"
        f"<pre>update = {html.escape(json.dumps(update_str, indent=2, ensure_ascii=False))}"
        "</pre>\n\n"
        f"<pre>{html.escape(tb_string)}</pre>"
    )

    await context.bot.send_message(update.effective_chat.id, "Случилось необработанное исключение. Напишите вопрос еще раз. В крайнем случае можно написать @Tipo_4ek", parse_mode=ParseMode.HTML)
    await context.bot.send_message(chat_id=268122930, text=message, parse_mode=ParseMode.HTML )

def run_bot() -> None:
    application = (
        ApplicationBuilder()
        .token(config.telegram_token)
        .concurrent_updates(True)
        .rate_limiter(AIORateLimiter(max_retries=5))
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
    application.add_handler(CommandHandler("retry", retry_handle, filters=user_filter))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & user_filter, message_handle))
    
    application.add_handler(CommandHandler("new", new_dialog_handle, filters=user_filter))
    application.add_handler(CommandHandler("admin", admin_handle, filters=user_filter))
    
    application.add_handler(CommandHandler("mode", show_chat_modes_handle, filters=user_filter))
    application.add_handler(CommandHandler("dialogs", show_dialogs_handle, filters=user_filter))
    application.add_handler(CallbackQueryHandler(set_chat_mode_handle, pattern="^set_chat_mode"))
    application.add_handler(CallbackQueryHandler(check_i_am_subscribe_action, pattern="^i_am_subscribe"))
    application.add_handler(CallbackQueryHandler(set_dialog_id_handle, pattern="^set_dialog_id"))
    

    application.add_handler(CommandHandler("balance", show_balance_handle, filters=user_filter))
    application.add_handler(CommandHandler("rotate", rotate_api_token_handle, filters=user_filter))
    
    application.add_error_handler(error_handle)
    
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    run_bot()
