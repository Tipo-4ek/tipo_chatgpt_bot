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
        "name": "👩🏼‍🎓 assistant (Болтун)",
        "welcome_message": "👩🏼‍🎓 Привет, я <b>ChatGPT assistant</b>. Можем пообщаться на разные темы. Я храню историю и отвечаю с контекстом. Чем могу быть полезен?",
        "prompt_start": "As an advanced chatbot named ChatGPT, your primary goal is to assist users to the best of your ability. This may involve answering questions, providing helpful information, or completing tasks based on user input. In order to effectively assist users, it is important to be detailed and thorough in your responses. Use examples and evidence to support your points and justify your recommendations or solutions. Remember to always prioritize the needs and satisfaction of the user. Your ultimate goal is to provide a helpful and enjoyable experience for the user."
    },

    "code_assistant": {
        "name": "👩🏼‍💻 Code assistant (Кодер)",
        "welcome_message": "👩🏼‍💻 Привет, я <b>ChatGPT кодер</b>. Могу написать код на разных ЯП, отрефакторить твой код или задокументировать его. Будет лучше, если вначале кода ты будешь сообщать ЯП фразой <code># language python</code>. Но ничего страшного, если забудешь. Хинт: если ты напишешь на английском - ответ будет лучше.\nЧем могу быть полезен?",
        "prompt_start": "As an advanced chatbot named ChatGPT, your primary goal is to assist users to write code. This may involve designing/writing/editing/describing code or providing helpful information. Where possible you should provide code examples to support your points and justify your recommendations or solutions. Make sure the code you provide is correct and can be run without errors. Be detailed and thorough in your responses. Your ultimate goal is to provide a helpful and enjoyable experience for the user. Write code inside <code>, </code> tags."
    },

    "movie_expert": {
        "name": "🎬 Movie expert (Кино эксперт)",
        "welcome_message": "🎬 Привет, я <b>ChatGPT Кино эксперт</b>. Я знаю очень много фильмов/мультиков/сериалов/аниме всего мира. Могу угадать фильм по описанию, порассуждать о каких-то моментах или напомнить название фильма, если вы его забыли. Хинт: если ты напишешь на английском - ответ будет лучше. \nЧем могу быть полезен?",
        "prompt_start": "As an advanced movie expert chatbot named ChatGPT, your primary goal is to assist users to the best of your ability. You can answer questions about movies, actors, directors, and more. You can recommend movies to users based on their preferences. You can discuss movies with users, and provide helpful information about movies. In order to effectively assist users, it is important to be detailed and thorough in your responses. Use examples and evidence to support your points and justify your recommendations or solutions. Remember to always prioritize the needs and satisfaction of the user. Your ultimate goal is to provide a helpful and enjoyable experience for the user."
    },

    "painter": {
        "name": "🖼️ Painter (Художник)",
        "welcome_message": "🖼️ Привет, я <b>ChatGPT художник основанный на DALL-E</b>. До MidJorney Мне еще далеко, но я могу сгенерировать картинку по твоему запросу. Попытайся писать очень подробные запросы. Чем больше подробностей - тем лучше результат. Хинт: если ты напишешь на английском - ответ будет лучше. Чем могу быть полезен?",
        "prompt_start": ""
        # "prompt_start": "As an advanced chatbot named ChatGPT, your primary goal is to assist users to write paintings. This may involve designing or providing paintings. You need to provide painting scatch to support your points and justify your recommendations or solutions. Be detailed and thorough in your responses. Your ultimate goal is to provide a helpful and enjoyable experience for the user. Write result as png/jpg or jpeg file."
    },
}


class ChatGPT:
    def __init__(self):
        pass
    
    def send_message(self, message, dialog_messages=[], chat_mode="CHOOSE \/MODE"):
        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            prompt = self._generate_prompt(message, dialog_messages, chat_mode)
            try:
                r = openai.Completion.create(
                    engine="text-davinci-003",
                    prompt=prompt,
                    temperature=0.7,
                    max_tokens=1000,
                    top_p=1,
                    frequency_penalty=0,
                    presence_penalty=0,
                )
                answer = r.choices[0].text
                answer = self._postprocess_answer(answer)
                

                n_used_tokens = r.usage.total_tokens

            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise ValueError("Достигли бесплатного дневного лимита. Попробуйте еще раз. Если не получится - ротируйте токен /rotate.") from e

            
            # forget first message in dialog_messages
        dialog_messages = dialog_messages[1:]

        n_first_dialog_messages_removed = n_dialog_messages_before - len(dialog_messages)

        return answer, prompt, n_used_tokens, n_first_dialog_messages_removed
    
    def send_photo(self, message, dialog_messages=[], chat_mode="CHOOSE \/MODE"):
        if chat_mode not in CHAT_MODES.keys():
            raise ValueError(f"Chat mode {chat_mode} is not supported")

        n_dialog_messages_before = len(dialog_messages)
        answer = None
        while answer is None:
            prompt = message
            try:
                r = openai.Image.create(
                    prompt=prompt,
                    n=2,
                    size="1024x1024"
                    )
                #image_url = r.data[0]['url']
                urls = []
                for data in r['data']:
                    urls.append(data['url'])
                
                answer = ""
                answer = ' '.join(urls)
                answer = self._postprocess_answer(answer)
                
                # $0.02 by 1 picture => 2000tokens == 1 picture.
                n_used_tokens = 2000
            except Exception as e:
                print (e)
                raise ValueError(e)

            except openai.error.InvalidRequestError as e:  # too many tokens
                if len(dialog_messages) == 0:
                    raise ValueError("Достигли бесплатного дневного лимита в картинках. Попробуйте еще раз. Если не получится - ротируйте токен /rotate. Mode Assistant должен работать без проблем") from e

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
        if (chat_mode != "painter"):
            prompt += f"User: {message}\n"
            prompt += "ChatGPT: "
        else: # choose paint | need to extra parameters
            prompt += f"User: {message}\n"
            prompt += "ChatGPT: "
        return prompt

    def _postprocess_answer(self, answer):
        answer = answer
        return answer
    
