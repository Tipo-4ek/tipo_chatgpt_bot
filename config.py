import yaml
import dotenv
from pathlib import Path

config_dir = Path(__file__).parent.parent.resolve() / "config"

# load yaml config
with open(config_dir / "config.yml", 'r') as f:
    config_yaml = yaml.safe_load(f)

# load .env config
config_env = dotenv.dotenv_values(config_dir / "config.env")

# config parameters
telegram_token = config_yaml["telegram_token"]
# openai_api_key = config_yaml["openai_api_key"]
openai_api_key_list = ["YOUR-OPENAI-API-KEY-1", "YOUR-OPENAI-API-KEY-2", "YOUR-OPENAI-API-KEY-3"]
allowed_telegram_usernames = config_yaml["allowed_telegram_usernames"]
new_dialog_timeout = config_yaml["new_dialog_timeout"]
mongodb_uri = f"mongodb://mongo:{config_env['MONGODB_PORT']}" # optional
mongo_client = "YOUR_DOCKER_MONGO_CLIENT_NAME" # optional

REQUIRED_CHATS_TO_SUBSCRIBE = {
    "tipo_community": {
        "id": "-1001827965752",
        "link": "https://t.me/tipo_chatgpt_community",
        "name": "Tipo ChatGPT Community"
    }
}
token_limits_per_day = 8000
provider_token = "000000:LIVE:00000" # provider token for telegram payments (from BotFather)
payload = "secret-payload-string"
DONATE_RATES = {
    "donate_250": 
        {"name": "🎁 Пожертвование 250₽", "description": "Вся денежная сумма переводится в качестве пожертвования на разработку https://t.me/tipo_chatgpt_bot бота", "price": 250, "type": "donate", "currency": "RUB"}, 
    "donate_500": 
        {"name": "🎁 Пожертвование 500₽", "description": "Вся денежная сумма переводится в качестве пожертвования на разработку https://t.me/tipo_chatgpt_bot бота", "price": 500, "type": "donate", "currency": "RUB"}, 
    "subscribe_month": 
        {"name": "🟢 Подписка на месяц (Подробности внутри →)", "description": "Месячная подписка на бота. Подписка подразумевает отсутствие лимитов на общение с ботом.", "price": 100, "type": "sub_month", "currency": "RUB"},
    "subscribe_halfYear": 
        {"name": "⚡Подписка на полгода (Подробности внутри →)", "description": "Полугодовая подписка на бота. Подписка подразумевает отсутствие лимитов на общение с ботом.", "price": 450, "type": "sub_halfYear", "currency": "RUB"},
    "subscribe_year": 
        {"name": "💎 Подписка на год (Подробности внутри →)", "description": "Годовая подписка на бота. Подписка подразумевает отсутствие лимитов на общение с ботом.", "price": 850, "type": "sub_year", "currency": "RUB"},
    "thanks": 
        {"name": "💜 Просто сказать спасибо"}
}
