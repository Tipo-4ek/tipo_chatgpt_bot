'''Part of this code is under the MIT license
MIT License

Copyright (c) 2023 Karim Iskakov
'''
from typing import Optional, Any
import json
import pymongo
import uuid
from datetime import datetime
import config

last_user_printed = 0
class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(config.mongodb_uri)
        self.db = self.client[config.mongo_client]
        self.user_collection = self.db["user"]
        self.dialog_collection = self.db["dialog"]

    def check_if_user_exists(self, user_id: int, raise_exception: bool = False):
        if self.user_collection.count_documents({"_id": user_id}) > 0:
            return True
        else:
            if raise_exception:
                raise ValueError(f"User {user_id} does not exist. Did You forget /start command?")
            else:
                return False
        
    def check_premium_expired(self, user_id: int):
        if ((self.get_user_attribute(user_id, "is_premium") == True) and (self.get_user_attribute(user_id, "premium_expired") < datetime.today())):
            self.set_user_attribute(user_id, "premium_expired", None)
            self.set_user_attribute(user_id, "is_premium", False)
            return False
        else:
            return True


    def show_all_users(self):
        collection = self.user_collection.find()
        result = json.dumps(list(collection), default=str, indent=4)
        return result
    
    def get_dialogs(self, user_id):
        collection = self.dialog_collection.find({"user_id": user_id}).sort("start_time", -1)
        result = json.dumps(list(collection), default=str, indent=4)
        return result

        

    def add_new_user(
        self,
        user_id: int,
        chat_id: int,
        username: str = "",
        first_name: str = "",
        last_name: str = "",
    ):
        user_dict = {
            "_id": user_id,
            "chat_id": chat_id,

            "username": username,
            "first_name": first_name,
            "last_name": last_name,

            "last_interaction": datetime.now(),
            "first_seen": datetime.now(),
            
            "current_dialog_id": None,
            "current_chat_mode": "assistant",

            "is_donater": False,
            "is_premium": False,
            "premium_expired": None,
            "n_used_tokens": 0,
            "n_used_tokens_today":0
        }

        if not self.check_if_user_exists(user_id):
            self.user_collection.insert_one(user_dict)
            
        # TODO: maybe start a new dialog here?

    def start_new_dialog(self, user_id: int):
        self.check_if_user_exists(user_id, raise_exception=True)

        dialog_id = str(uuid.uuid4())
        dialog_dict = {
            "_id": dialog_id,
            "user_id": user_id,
            "chat_mode": self.get_user_attribute(user_id, "current_chat_mode"),
            "start_time": datetime.now(),
            "messages": []
        }


        # add new dialog
        self.dialog_collection.insert_one(dialog_dict)
        # update user's current dialog
        self.user_collection.update_one(
            {"_id": user_id},
            {"$set": {"current_dialog_id": dialog_id}}
        )

        return dialog_id

    def get_user_attribute(self, user_id: int, key: str):
        self.check_if_user_exists(user_id, raise_exception=True)
        user_dict = self.user_collection.find_one({"_id": user_id})
        global last_user_printed
        if (last_user_printed != user_id): # Removing duplicate user_dict from log.log
            with open("log.log", "a") as log_file:
                    log_file.write(f"\ndebug --> user_dict {user_dict}")
            last_user_printed = user_id
        else: 
            print ("user_dict", user_dict)
            pass

        if key not in user_dict:
            raise ValueError(f"User {user_id} does not have a value for {key}")

        return user_dict[key]

    def set_user_attribute(self, user_id: int, key: str, value: Any):
        self.check_if_user_exists(user_id, raise_exception=True)
        self.user_collection.update_one({"_id": user_id}, {"$set": {key: value}})

    def get_dialog_messages(self, user_id: int, dialog_id: Optional[str] = None):
        self.check_if_user_exists(user_id, raise_exception=True)

        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")

        dialog_dict = self.dialog_collection.find_one({"_id": dialog_id, "user_id": user_id})
        return dialog_dict["messages"]

    def set_dialog_messages(self, user_id: int, dialog_messages: list, dialog_id: Optional[str] = None):
        self.check_if_user_exists(user_id, raise_exception=True)

        if dialog_id is None:
            dialog_id = self.get_user_attribute(user_id, "current_dialog_id")
        
        self.dialog_collection.update_one(
            {"_id": dialog_id, "user_id": user_id},
            {"$set": {"messages": dialog_messages}}
        )
