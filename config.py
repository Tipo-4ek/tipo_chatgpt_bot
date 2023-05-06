'''
-------------------------------------------
  Copyright (c) 2023 Tipo-4ek
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.
  
'''

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