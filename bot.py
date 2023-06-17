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
import concurrent.futures
import time
from datetime import datetime, time, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import telegram
import threading
import schedule
import sched
from telegram import Update, User, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, LabeledPrice
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    PreCheckoutQueryHandler,
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

HELP_MESSAGE = f"""Commands:
⚪ /mode – Выбрать режим работы бота
⚪ /new – Забыть контекст и начать новую сессию диалога
⚪ /balance – Остаток доступных токенов, премиум статус и др.
⚪ /dialogs – Показать прошлые диалоги и переключиться на один из них
⚪ /help – Показать доступные команды и их описание

🎁 Вам доступен бесплатный дневной лимит в {config.token_limits_per_day} токенов. 
Напишите /mode для выбора режима чат-бота (Ассистент, кодер, киноэксперт, художник)
----
Owner – @Tipo_4ek
Support the developer - /donate
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
    
async def check_premium_expired_handle(update: Update):
    user_id = update.effective_chat.id
    if (db.check_premium_expired(user_id) == False):
        await update.message.reply_text(f"Ваша подписка истекла :(\nВы можете продлить ее командой /subscribe или использовать бесплатные дневной лимит", parse_mode=ParseMode.HTML)
    return True

def reset_daily_limits():
    all_users_json = db.show_all_users()
    # users_count && last_username
    json_list = json.loads(all_users_json)    
    
    users_chat_ids = []
    for user in json_list:
        print (user)
        if 'chat_id' in user:
            users_chat_ids.append(user['chat_id'])
    for user_chat_id in users_chat_ids:
        db.set_user_attribute(user_chat_id, "n_used_tokens_today", 0)
    print('Resetting daily limits at', datetime.now())
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
    user_id = update.effective_chat.id
    await register_user_if_not_exists(update, context, update.effective_chat)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)
    
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
    await check_premium_expired_handle(update)
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await update.message.reply_text(HELP_MESSAGE, parse_mode=ParseMode.HTML)


async def retry_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    if await is_previous_message_not_answered_yet(update, context): return
    await check_premium_expired_handle(update)
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    dialog_messages = db.get_dialog_messages(user_id, dialog_id=None)
    if len(dialog_messages) == 0:
        await update.message.reply_text("Нечего повторять :\ 🤷‍♂️")
        return

    last_dialog_message = dialog_messages.pop()
    db.set_dialog_messages(user_id, dialog_messages, dialog_id=None)  # last message was removed from the context
    print ("retry. Message ", last_dialog_message["user"])
    await message_handle(update, context, message=last_dialog_message["user"], use_new_dialog_timeout=False)


async def message_handle(update: Update, context: CallbackContext, message=None, use_new_dialog_timeout=True):
    user_id = update.effective_chat.id
    if await check_required_subscriptions(update, context, update.effective_chat): return
    if await is_previous_message_not_answered_yet(update, context): return
    await check_premium_expired_handle(update)
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

        # check free quota exceed or premium status
        if ((db.get_user_attribute(user_id, "n_used_tokens_today") < config.token_limits_per_day) or ((db.get_user_attribute(user_id, "is_premium") == True) and (db.get_user_attribute(user_id, "premium_expired") != None and  (db.get_user_attribute(user_id, "premium_expired") >= datetime.today())))):
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
                db.set_user_attribute(user_id, "n_used_tokens", n_used_tokens + db.get_user_attribute(user_id, "n_used_tokens"))
                db.set_user_attribute(user_id, "n_used_tokens_today", n_used_tokens + db.get_user_attribute(user_id, "n_used_tokens_today"))
            except Exception as e:
                if "is not subscriptable" in str(e):
                    error_text = "Где-то правили базу. Напиши /start еще раз, пожалуйста"
                else:
                    error_text = f"Чот пошло не так. {e}"
                logger.error(error_text)
                await update.message.reply_text(error_text)
                return
            except asyncio.CancelledError:
                print ("cancelerror")
                # await update.message.reply_text("Сорри, но openai не вернула ответ на запрос")
                pass
            


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
                        # got not md
                        if len(answer) > 4096:
                            for x in range(0, len(answer), 4096):
                                await update.message.reply_text(answer[x:x+4096], parse_mode=parse_mode)
                        else:
                            await update.message.reply_text(answer, parse_mode=parse_mode)
                else:
                    #print ("PAINTER AWAIT")
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
        
        else:
            await update.message.reply_text(f"<b>[RU]</b>\nБесплатный лимит токенов закончился.\n Актуальный баланс вы можете посмотреть в /balance \n\nВы можете УБРАТЬ ЛИМИТЫ и получить ⭐<b>PREMIUM</b>⭐ статус. Достаточно лишь приобрести подписку на бота в разделе /subscribe.\n\n<b>[EN]</b>\nThe free token limit has ended.\nYou can view the current balance in /balance.\n\nYou can REMOVE the LIMITS and get ⭐<b>PREMIUM</b>⭐ status. It is enough just to purchase a subscription to the bot in the /subscribe section", parse_mode=ParseMode.HTML)

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
    await check_premium_expired_handle(update)

    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    db.start_new_dialog(user_id)
    await update.message.reply_text("Начали новый диалог ✅\nЕсли вы хотите продолжить старый диалог - используйте /dialog")

    chat_mode = db.get_user_attribute(user_id, "current_chat_mode")
    await update.message.reply_text(f"{chatgpt.CHAT_MODES[chat_mode]['welcome_message']}", parse_mode=ParseMode.HTML)

async def admin_handle(update: Update, context: CallbackContext):
    # secret stat
    pass
    

def get_chat_modes_page(page_num: int):
    n_chat_modes_per_page = 5
    text = f"[RU]\nВыберите режим бота. (Доступно {len(chatgpt.CHAT_MODES.items())})\n[EN]\nSelect chat mode. (Available {len(chatgpt.CHAT_MODES.items())})"
    chat_mode_keys = list(chatgpt.CHAT_MODES.keys())
    print (f"chat_modes_keys = {chat_mode_keys}")
    page_chat_mode_keys = chat_mode_keys[page_num * n_chat_modes_per_page:(page_num + 1) * n_chat_modes_per_page]
    print (f"page_chat_mode_keys {page_chat_mode_keys}")
    keyboard = []
    for chat_mode_key in page_chat_mode_keys:
        keyboard.append([InlineKeyboardButton(chatgpt.CHAT_MODES[chat_mode_key]["name"], callback_data=f"set_chat_mode|{chat_mode_key}")])
    
    # chat modes pagination
    if len(chat_mode_keys) > n_chat_modes_per_page:
        is_first_page = (page_num == 0)
        is_last_page = ((page_num + 1) * n_chat_modes_per_page >= len(chat_mode_keys))

        if is_first_page:
            keyboard.append([
                InlineKeyboardButton("»", callback_data=f"show_chat_modes|{page_num + 1}")
            ])
        elif is_last_page:
            keyboard.append([
                InlineKeyboardButton("«", callback_data=f"show_chat_modes|{page_num - 1}"),
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("«", callback_data=f"show_chat_modes|{page_num - 1}"),
                InlineKeyboardButton("»", callback_data=f"show_chat_modes|{page_num + 1}")
            ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    return text, reply_markup

async def show_chat_modes_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.effective_chat)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    text, reply_markup = get_chat_modes_page(0)
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)

async def show_chat_modes_callback_handle(update: Update, context: CallbackContext):
     user_id = update.callback_query.from_user.id
     db.set_user_attribute(user_id, "last_interaction", datetime.now())

     query = update.callback_query
     await query.answer()

     page_index = int(query.data.split("|")[1])
     if page_index < 0:
         return

     text, reply_markup = get_chat_modes_page(page_index)
     try:
         await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=ParseMode.HTML)
     except telegram.error.BadRequest as e:
         if str(e).startswith("Message is not modified"):
             pass
def start_daily_reset():
    print ("Start daily reset func")
    reset_daily_limits()

async def show_dialogs_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.effective_chat)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)
    user_id = update.effective_chat.id
    keyboard = []

    dialogs = db.get_dialogs(user_id = user_id)
    json_list = json.loads(dialogs)
    for d in json_list:
        if (d["messages"]):
            # not empty dialog found
            dialog_start_time = d["start_time"][:16]
            dialog_shortcut = dialog_start_time + " " + d["messages"][0]["user"][:50]
            dialog_id = d["_id"]
            dialog_mode = d["chat_mode"]
            keyboard.append([InlineKeyboardButton(dialog_shortcut, callback_data=f"set_dialog|{dialog_id}|{dialog_mode.strip()}")]) # callback_data have max len str... if dialog_mode were too long --> exception telegram.error.BadRequest: Button_data_invalid
    reply_markup = InlineKeyboardMarkup(keyboard[:10])
    if (keyboard != []):
        await context.bot.send_message(chat_id=user_id, text="↓ Select your dialog:", reply_markup=reply_markup)
    else:
        await context.bot.send_message(chat_id=user_id, text="No dialogs found. Maybe you wanted to start a /new dialog?")

async def set_chat_mode_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)
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
    await check_premium_expired_handle(update)
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    dialog_id = query.data.split("|")[1].split(' ')[0]
    dialog_chat_mode = query.data.split("|")[2].split(' ')[0]
    with open("log.log", "a") as log_file:
                log_file.write(f"\ndebug --> /dialog CHANGED to {update.callback_query.from_user.username} > {dialog_id} and chat_mode = {dialog_chat_mode}")
    db.set_user_attribute(user_id, "current_dialog_id", dialog_id)
    db.set_user_attribute(user_id, "current_chat_mode", dialog_chat_mode)

    await query.edit_message_text(f"Контекст диалога успешно изменен")


async def want_to_pay_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update.callback_query, context, update.callback_query.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)
    user_id = update.callback_query.from_user.id

    query = update.callback_query
    await query.answer()

    item_to_pay = query.data.split("|")[1]
    await query.edit_message_text(f"Счет будет ниже")
    await send_invoice_handle(update, context, item_to_pay)

async def thanks_handle(update:Update, context:CallbackContext):
    user_id = update.callback_query.from_user.id
    await context.bot.send_message(chat_id=268122930, text=f"Thanks message recieved from {user_id}")
    await context.bot.send_message(chat_id=user_id, text=f"💘 Thanks message send to developer. ")

async def show_balance_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)

    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    n_used_tokens_today = db.get_user_attribute(user_id,"n_used_tokens_today")
    n_used_tokens = db.get_user_attribute(user_id, "n_used_tokens")
    tokens_left = config.token_limits_per_day - n_used_tokens_today
    if (tokens_left < 0):
        tokens_left = 0
    text = f"Всего на один api key бесплатно выделено $18/3мес.\n<code>Картинка 1024х1024 весит $0.02</code>.\n<code>Текст $0.002/1000 токенов.</code>\n\nМатематика приблизительно такая:\n<code>1 токен - 4 латинских символа</code>\n<code>30 токенов - 1-2 предложения</code>\n<code>100 токенов - 75 букв</code>\nВ боте предусмотрена полуавтоматическая (командой в бота) ротация токена, в случае, если токен протух/кончилась квота.\n\n"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)
    text = ""
    if ((db.get_user_attribute(user_id,"is_donater") != None) and (db.get_user_attribute(user_id,"is_donater") == True)):
        text += f"Вижу, что вы донатили! Спасибо за поддержку! 💘\n\n"
    if ((db.get_user_attribute(user_id,"is_premium") != None) and (db.get_user_attribute(user_id,"is_premium") == True)):
        text += f"Вы ⭐PREMIUM⭐ пользователь. Спасибо за поддержку! 💜\n\n"
        text += f"Потрачено токенов <b>сегодня</b> <code>{n_used_tokens_today}</code> <i>.</i>\n"
    else:
        text += f"К сожалению, у вас нет ⭐PREMIUM⭐ статуса.\nОднако его всегда можно приобрести за символическую плату в /subscribe\n\n"
        text += f"Потрачено токенов <b>сегодня</b> <code>{n_used_tokens_today}</code> <i>.</i>\n"
        text += f"Осталось токенов на сегодня - <code>{tokens_left}</code> <i>.</i>\n"
    
    
    text += f"Потрачено токенов <b>Всего</b> - <code>{n_used_tokens}</code> <i>.</i>\n"

    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def rotate_api_token_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    if await check_required_subscriptions(update, context, update.effective_chat): return
    await check_premium_expired_handle(update)
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())

    token_index = chatgpt.rotate_token()
    text = f"Ротация токена успешно произведена. Текущий токен - {token_index}\n"
    await context.bot.send_message(chat_id=268122930, text=f"TOKEN ROTATED by {user_id}.\nТекущий токен - {token_index}\nCHECK BOT CONDITION")
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

async def donate_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    keyboard = []
    for item, value in config.DONATE_RATES.items():
        if ("donate" in item):
            keyboard.append([InlineKeyboardButton(value["name"], callback_data=f"want_to_pay|{item}")])
        if ("thanks" in item):
            keyboard.append([InlineKeyboardButton(value["name"], callback_data=f"thanks")])    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "💲 You can also pay the invoice in Webmoney WMZ. Contact me to do this -> https://t.me/tipo_4ek"
    await context.bot.send_message(chat_id=user_id, text=text)
    await context.bot.send_message(chat_id=user_id, text="Выберите тип доната:", reply_markup=reply_markup)    
    
    

async def paid_subscription_handle(update: Update, context: CallbackContext):
    await register_user_if_not_exists(update, context, update.message.from_user)
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    keyboard = []
    for item, value in config.DONATE_RATES.items():
        if ("subscribe" in item):
            keyboard.append([InlineKeyboardButton(value["name"], callback_data=f"want_to_pay|{item}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    if (db.get_user_attribute(user_id, "is_premium") == True):
        expired_date = db.get_user_attribute(user_id, 'premium_expired').strftime('%Y-%m-%d %H:%M:%S')

        text = f"У вас уже <b>есть премиум</b> подписка\nВаша подписка истекает {expired_date} (UTC+0)\n💘"
        await context.bot.send_message(chat_id=user_id, text=text, parse_mode=ParseMode.HTML)
    else:
        text = "💲 You can also pay the invoice in Webmoney WMZ. Contact me to do this -> https://t.me/tipo_4ek"
        await context.bot.send_message(chat_id=user_id, text=text)
        await context.bot.send_message(chat_id=user_id, text="Выберите тип подписки", reply_markup=reply_markup)


async def successful_payment_handle(update, context):
    user_id = update.effective_chat.id
    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    paid_item = update.message.successful_payment.invoice_payload.split("|")[1]
    for item, value in config.DONATE_RATES.items(): 
        if (item == paid_item):
            title = value["name"]
            description = value["description"]
            if ("subscribe" in item):
                period = item.split("_")[1]
                if (period == "month"):
                    date_expired = datetime.today() + timedelta(days=31)
                elif (period == "halfYear"):
                    date_expired = datetime.today() + timedelta(days=181)
                elif (period == "year"):
                    date_expired = datetime.today() + timedelta(days=366)
                await update.message.reply_text(f"Спасибо, мы получили ваш платеж!\nКупленная услуга - {title}\n{description}\nДата окончания услуги - {date_expired.strftime('%Y-%m-%d')}\n\nПо вопросам обращайтесь к @Tipo_4ek")
                
                db.set_user_attribute(user_id, "is_premium", True)
                db.set_user_attribute(user_id, "premium_expired", date_expired)
            else:
                db.set_user_attribute(user_id, "is_donater", True)
                await update.message.reply_text(f"Спасибо, ваш платеж получен!\nКупленная услуга - {title}\n{description}\n\nПо вопросам обращайтесь к @Tipo_4ek")

    db.set_user_attribute(user_id, "last_interaction", datetime.now())
    await context.bot.send_message(chat_id=268122930, text=f"Хто-то задонатил! :)\nКупленная услуга - {paid_item}\nuser - {user_id}\n\n")



async def send_invoice_handle(update: Update, context: CallbackContext, payment_type="None"):
    title = "Пожертвование(donation)"
    description = "Вся денежная сумма переводится в качестве пожертвования на разработку https://t.me/tipo_chatgpt_bot бота"
    currency = "RUB"
    labeled_prices = []
    provider_data = {}
    provider_data["receipt"] = {}
    provider_data["receipt"]["items"] = []
    for item, value in config.DONATE_RATES.items(): 
        if (item == payment_type):
            labeled_price = LabeledPrice(value["name"], value["price"] * 100)
            labeled_prices.append(labeled_price)
            title = value["name"]
            description = value["description"]
            payload = config.payload + "|" + item # bytes(update.effective_chat.id + "_" + str(time.time()), "utf-8")
            provider_token = config.provider_token
            currency = value["currency"]
            # --
            item_data = {}
            item_data["description"] = value["description"]
            item_data["quantity"] = "1.00"
            item_data["amount"] = {"value": "{:.2f}".format(value["price"]), "currency": value["currency"]}
            item_data["vat_code"] = 1
            provider_data["receipt"]["items"].append(item_data)

    # преобразовать данные поставщика в JSON формат
    provider_data_json = json.dumps(provider_data, ensure_ascii=False)
    await context.bot.sendInvoice(update.effective_chat.id, title, description, payload, provider_token, currency, labeled_prices, need_email = True, send_email_to_provider = True, provider_data = provider_data_json)
    # await update.edited_message.reply_text(text)

async def handle_invoice(update, context):
    payload = config.payload
    query = update.pre_checkout_query
    if query.invoice_payload.split("|")[0] != payload:
        await context.bot.answer_pre_checkout_query(
            pre_checkout_query_id=query.id,
            ok=False,
            error_message='Что-то пошло не так...',
        )
    else:
        await context.bot.answer_pre_checkout_query(pre_checkout_query_id=query.id, ok=True)

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
    application.add_handler(CallbackQueryHandler(show_chat_modes_callback_handle, pattern="^show_chat_modes"))
    application.add_handler(CallbackQueryHandler(check_i_am_subscribe_action, pattern="^i_am_subscribe"))
    application.add_handler(CallbackQueryHandler(set_dialog_id_handle, pattern="^set_dialog"))
    application.add_handler(CallbackQueryHandler(want_to_pay_handle, pattern="^want_to_pay"))
    application.add_handler(CallbackQueryHandler(thanks_handle, pattern="^thanks"))

    application.add_handler(CommandHandler("balance", show_balance_handle, filters=user_filter))
    application.add_handler(CommandHandler("rotate", rotate_api_token_handle, filters=user_filter))
    application.add_handler(CommandHandler("donate", donate_handle, filters=user_filter))
    application.add_handler(CommandHandler("subscribe", paid_subscription_handle, filters=user_filter))
    application.add_handler(PreCheckoutQueryHandler(handle_invoice))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handle))
    application.add_error_handler(error_handle)
    
    # start the bot
    application.run_polling()


if __name__ == "__main__":
    # Создание планировщика в фоновом режиме
    sched = BackgroundScheduler()
    # Задача для запуска ежедневного сброса в 0:00
    sched.add_job(start_daily_reset, 'cron', timezone="Europe/Moscow", hour=00, minute=00)
    # Запуск планировщика в отдельном потоке
    t = threading.Thread(target=sched.start)
    t.start()
    run_bot()
