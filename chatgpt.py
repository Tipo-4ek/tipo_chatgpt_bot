import config
import openai

openai_api_key_list = config.openai_api_key_list
openai.api_key


def init_api_key (n=0):
    openai.api_key = openai_api_key_list[n]
    
def rotate_token():
    index = 0
    for i in openai_api_key_list:
        if (i == openai.api_key):
            if (index < len(openai_api_key_list) - 1):
                init_api_key(index + 1)
            else:
                init_api_key(0)
            break
        index+=1
    return index


CHAT_MODES = {
    "assistant": {
        "name": "👩🏼‍🎓 Разговорный бот (assistant)",
        "welcome_message": "👩🏼‍🎓 Привет, я <b>ChatGPT assistant</b>. Модель gpt-3.5-turbo Можем пообщаться на разные темы. Я храню историю и отвечаю с контекстом. Чем могу быть полезен?",
        "prompt_start": "As an advanced chatbot named Tipo ChatGPT, your primary goal is to assist users to the best of your ability. This may involve answering questions, providing helpful information, or completing tasks based on user input. In order to effectively assist users, it is important to be detailed and thorough in your responses. Use examples and evidence to support your points and justify your recommendations or solutions. Remember to always prioritize the needs and satisfaction of the user. Your ultimate goal is to provide a helpful and enjoyable experience for the user.",
        "parse_mode": "HTML"
    },

    "code_assistant": {
        "name": "👩🏼‍💻 Разработчик (Code assistant)",
        "welcome_message": "👩🏼‍💻 Привет, я <b>ChatGPT кодер</b>. Могу написать код на разных ЯП, отрефакторить твой код или задокументировать его. Будет лучше, если вначале кода ты будешь сообщать ЯП фразой <code># language python</code>. Но ничего страшного, если забудешь. Хинт: если ты напишешь на английском - ответ будет лучше.\nЧем могу быть полезен?",
        "prompt_start": "As an advanced chatbot named ChatGPT, your primary goal is to assist users to write code. This may involve designing/writing/editing/describing code or providing helpful information. Where possible you should provide code examples to support your points and justify your recommendations or solutions. Make sure the code you provide is correct and can be run without errors. Be detailed and thorough in your responses. Your ultimate goal is to provide a helpful and enjoyable experience for the user. Format output in Markdown.",
        "parse_mode": "markdown"
    },
    "painter": {
        "name": "🖼️ Художник (Painter)",
        "welcome_message": "🖼️ Привет, я <b>ChatGPT художник основанный на DALL-E</b>. До MidJorney Мне еще далеко, но я могу сгенерировать картинку по твоему запросу. Попытайся писать очень подробные запросы. Чем больше подробностей - тем лучше результат. Хинт: если ты напишешь на английском - ответ будет лучше. Чем могу быть полезен?",
        "prompt_start": "",
        "parse_mode": "HTML"
    },
    "quotes": {
        "name": "🐺 Пацанские цитаты с волками (Boy quotes)",
        "welcome_message": "🐺 Привет, я <b>генератор пацанских цитат</b>. Брат, волк это волк, пока он воет.",
        "prompt_start": "You're a chatbot that generates the stupidest kid quotes. Your task is to generate incorrect quotes that can be considered brilliant. It is ideal to start a quote with the address wolf or brother. The more illogical the quote, the better. Answer in the language in which the user communicates with you",
        "parse_mode": "HTML"
    },
    "sql_assistant": {
        "name": "📊 SQL Помощник (SQL Assistant)",
        "welcome_message": "🖼️ Привет, я <b>SQL помощник</b>. Чем могу быть помочь?",
        "prompt_start": "You're advanced chatbot SQL Assistant. Your primary goal is to help users with SQL queries, database management, and data analysis. Provide guidance on how to write efficient and accurate SQL queries, and offer suggestions for optimizing database performance. Format output in Markdown.",
        "parse_mode": "markdown"
    },
    "rick_sanchez": {
        "name": "🥒 Рик Санчез (Rick from Rick and Morty)",
        "welcome_message": "🥒 Йоу, я <b>Рик Санчез</b>. Чего надо?",
        "prompt_start": "You're Rick Sanchez. You act, respond and answer like Rick Sanchez. You use the tone, manner and vocabulary Rick Sanchez would use. Do not write any explanations. Only answer like Rick Sanchez. You must know all of the knowledge of Rick Sanchez.",
        "parse_mode": "HTML"
    },
    "chef": {
        "name": "🍳 Кулинарный повар (Сhef)",
        "welcome_message": "🍳 Привет, я <b>кулинарный повар</b>. Подскажу рецепт или расскажу о блюде. Спрашивай!",
        "prompt_start": "You are an advanced culinary chef. Your main goal is to help users with questions about dishes, recipes and cooking history. Provide recommendations for writing effective and accurate recipes and offer similar dishes to what the user will request. Format the output in Markdown. Answer in the language in which the user communicates with you",
        "parse_mode": "markdown"
    },
    "english_professor": {
        "name": "🇬🇧 Репетитор по английскому (English tutor)",
        "welcome_message": "🇬🇧 Привет, я <b>репетитор по английскому языку</b>. Помогу тебе выучить английский или расширить словарный запас. Спрашивай!",
        "prompt_start": "You are an advanced chatbot assistant English tutor. You can help users learn and practice English, including grammar, vocabulary, pronunciation and speaking skills. You can also provide recommendations on learning resources and teaching methods. Your ultimate goal is to help users improve their English language skills and become more confident native English speakers.",
        "parse_mode": "HTML"
    },
    "russian_professor": {
        "name": "🇷🇺 Репетитор по русскому (Russian tutor)",
        "welcome_message": "🇷🇺 Привет, я <b>репетитор по русскому языку</b>. Помогу тебе выучить английский или расширить словарный запас. Спрашивай!",
        "prompt_start": "You are an advanced chatbot assistant Russian tutor. You can help users learn and practice Russian, including grammar, vocabulary, pronunciation and speaking skills. You can also provide recommendations on learning resources and teaching methods. Your ultimate goal is to help users improve their Russian language skills and become more confident native Russian speakers.",
        "parse_mode": "HTML"
    },
    "movie_expert": {
        "name": "🎬 Кино эксперт (Movie expert)",
        "welcome_message": "🎬 Привет, я <b>ChatGPT Кино эксперт</b>. Я знаю очень много фильмов/мультиков/сериалов/аниме всего мира. Могу угадать фильм по описанию, порассуждать о каких-то моментах или напомнить название фильма, если вы его забыли. Хинт: если ты напишешь на английском - ответ будет лучше. \nЧем могу быть полезен?",
        "prompt_start": "As an advanced movie expert chatbot named Tipo ChatGPT, your primary goal is to assist users to the best of your ability. You can answer questions about movies, actors, directors, and more. You can recommend movies to users based on their preferences. You can discuss movies with users, and provide helpful information about movies. In order to effectively assist users, it is important to be detailed and thorough in your responses. Use examples and evidence to support your points and justify your recommendations or solutions. Remember to always prioritize the needs and satisfaction of the user. Your ultimate goal is to provide a helpful and enjoyable experience for the user.",
        "parse_mode": "HTML"
    }
}


class ChatGPT:
    def __init__(self):
        pass
    
    async def send_message(self, message, dialog_messages=[], chat_mode="CHOOSE \/MODE"):
        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            with open("log.log", "a") as log_file:
                log_file.write(f"\ndebug --> Юзер > {chat_mode} |>| {message}")
        
            prompt = self._generate_gpt_3_model_prompt(message, dialog_messages, chat_mode)
            try:
                r = await openai.ChatCompletion.acreate(
                    model="gpt-3.5-turbo",
                    messages=prompt,
                    max_tokens = 1000
                )
                answer = r.choices[0].message.content
                answer = self._postprocess_answer(answer)
                

                n_used_tokens = r.usage.total_tokens

            except openai.error.RateLimitError as e: # billing hard limit has reached
                print (e)
                raise ValueError("Достигли бесплатного дневного лимита. Попробуйте еще раз. Если не получится - ротируйте токен /rotate.") from e
            except openai.error.InvalidRequestError as e:  # too many tokens
                print (e)
                if ("safaty system" in str(e)): # prompt is not safety secured
                    raise ValueError(f"Ваш запрос был отклонен системой защиты. Пожалуйста, переформулируйте его, убрав запросы 18+") from e
                if ("This model's maximum context length"):
                    raise ValueError(f"Достигли лимита в контексте. Кажется, бот вам отправляет большие ответы. Не хочется криво резать историю переписки без вашего ведома. \n\nПожалуйста, используйте /new и сформулируйте одно сообщение на основе диалога ♥") from e
                else:
                    
                    raise ValueError(f"Случилось непредвиденное. Скорее всего кончилась квота. Попробуйте использовать /rotate и напишите любое сообщение. Если бот не ответит - зовите Tipo_4ek@. Кстати - вот ошибка: {e}") from e
            except openai.error.Timeout as e:
                #Handle timeout error, e.g. retry or log
                print(f"OpenAI API request timed out: {e}")
                raise ValueError("API OpenAI Упало. Ждемс...") from e
            except openai.error.APIError as e:
                #Handle API error, e.g. retry or log
                print(f"OpenAI API returned an API Error: {e}")
                raise ValueError(f"OpenAI вернуло ошибку {e}") from e
            except openai.error.APIConnectionError as e:
                #Handle connection error, e.g. check network or log
                print(f"OpenAI API request failed to connect: {e}")
                raise ValueError(f"Не смогли соединиться с openAI. Либо сбои у них, либо у нашего сервера. Call Tipo_4ek@") from e
            except openai.error.AuthenticationError as e:
                #Handle authentication error, e.g. check credentials or log
                print(f"OpenAI API request was not authorized: {e}")
                raise ValueError(f"Стухла авторизация до openAI API. Call Tipo_4ek@") from e
            except openai.error.PermissionError as e:
                #Handle permission error, e.g. check scope or log
                print(f"OpenAI API request was not permitted: {e}")
                raise ValueError(f"Что-то с доступом до api. Call Tipo_4ek@") from e
            except Exception as e:
                print (e)
                raise ValueError(e)
            
            # forget first message in dialog_messages
        dialog_messages = dialog_messages[1:]

        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)

        return answer, prompt, n_used_tokens, n_first_dialog_messages_removed
    
    async def send_photo(self, message, dialog_messages=[], chat_mode="CHOOSE \/MODE"):
        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            prompt = message
            try:
                with open("log.log", "a") as log_file:
                    log_file.write(f"\ndebug --> Генерим картинку {prompt}")
                r = await openai.Image.acreate(
                    prompt=prompt,
                    n=2,
                    size="1024x1024"
                    )
                #image_url = r.data[0]['url']
                urls = []
                for data in r['data']:
                    urls.append(data['url'])
                with open("log.log", "a") as log_file:
                    log_file.write(f"\ndebug --> собрали ссылки на картинки {urls}------------------")
                answer = prompt
                #answer = ' '.join(urls)
                #answer = self._postprocess_answer(answer)
                
                # $0.02 by 1 picture => 20 000 tokens (gpt 3.5 turbo $0.002 per 1k) == 1 picture. 
                n_used_tokens = 40000
            
            except openai.error.RateLimitError as e: # billing hard limit has reached
                print (e)
                raise ValueError("Достигли бесплатного дневного лимита в картинках. Попробуйте еще раз. Если не получится - ротируйте токен /rotate.") from e
            except openai.error.InvalidRequestError as e:  # too many tokens
                print (e)
                dialog_messages = dialog_messages[1:]
                n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)
                raise ValueError("Случилось непредвиденное. Скорее всего кончилась квота и поможет ротация токена. Используйте /rotate и напишите любое сообщение. Если бот не ответит - зовите Tipo_4ek@") from e
            except openai.error.Timeout as e:
                #Handle timeout error, e.g. retry or log
                print(f"OpenAI API request timed out: {e}")
                raise ValueError("API OpenAI Упало. Ждемс...") from e
            except openai.error.APIError as e:
                #Handle API error, e.g. retry or log
                print(f"OpenAI API returned an API Error: {e}")
                raise ValueError(f"OpenAI вернуло ошибку {e}") from e
            except openai.error.APIConnectionError as e:
                #Handle connection error, e.g. check network or log
                print(f"OpenAI API request failed to connect: {e}")
                raise ValueError(f"Не смогли соединиться с openAI. Либо сбои у них, либо у нашего сервера. Call Tipo_4ek@") from e
            except openai.error.AuthenticationError as e:
                #Handle authentication error, e.g. check credentials or log
                print(f"OpenAI API request was not authorized: {e}")
                raise ValueError(f"Стухла авторизация до openAI API. Call Tipo_4ek@") from e
            except openai.error.PermissionError as e:
                #Handle permission error, e.g. check scope or log
                print(f"OpenAI API request was not permitted: {e}")
                raise ValueError(f"Что-то с доступом до api. Call Tipo_4ek@") from e
            except Exception as e:
                print (e)
                raise ValueError(e)


        # forget first message in dialog_messages
        dialog_messages = dialog_messages[1:]
        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)

        return answer, prompt, n_used_tokens, n_first_dialog_messages_removed, urls[0], urls


    def _generate_prompt(self, message, dialog_messages, chat_mode):
        prompt = CHAT_MODES[chat_mode]["prompt_start"]
        prompt += "\n\n"
        # add chat context
        if len(dialog_messages) > 0:
            prompt += "Chat:\n"
            for dialog_message in dialog_messages:
                prompt += f"User: {dialog_message['user']}\n"
                prompt += f"ChatGPT: {dialog_message['bot']}\n"

        # current message
        prompt += f"User: {message}\n"
        prompt += "ChatGPT: "
        return prompt

    def _generate_gpt_3_model_prompt(self, message, dialog_messages, chat_mode):
        messages = []
        message_dict = {}
        message_dict["role"] = "system"
        message_dict["content"] = CHAT_MODES[chat_mode]["prompt_start"]
        messages.append(message_dict)

        # add chat context
        if len(dialog_messages) > 0:
            for dialog_message in dialog_messages:
                message_dict = {}
                message_dict["role"] = "user"
                message_dict["content"] = dialog_message['user']
                messages.append(message_dict)
                message_dict = {}
                message_dict["role"] = "assistant"
                message_dict["content"] = dialog_message['bot']
                messages.append(message_dict)

        # current message
        message_dict = {}
        message_dict["role"] = "user"
        message_dict["content"] = message
        messages.append(message_dict)
        return messages

    def _postprocess_answer(self, answer):
        answer = answer
        return answer
    
