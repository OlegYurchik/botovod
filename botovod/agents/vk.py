import botovod
from botovod import utils
import json
import logging
import requests
from threading import Thread
import time



class Agent(botovod.Agent):
    api_url = "https://api.vk.com/method"
    bot_url = "{server}?act=a_check&key={key}&ts={ts}&wait={wait}"
    user_url = "https://{server}?act=a_check&key={key}&ts={ts}&wait={wait}&mode={mode}&version={version}"

    def __init__(self, manager, name, token, group_id, api_version="5.50", method="callback",confirm_key=None,
                 secret_key=None, polling_wait=25, polling_delay=5, polling_daemon=False):
        super().__init__(manager, name)
        self.token = token
        self.group_id = group_id
        self.api_version = api_version
        self.method = method
        
        self.confirm_key = confirm_key
        self.secret_key = secret_key

        self.polling_wait = polling_wait
        self.polling_delay = polling_delay
        self.polling_daemon = polling_daemon
        
        self.polling_key = None
        self.polling_server = None
        self.polling_ts = None
        self.polling_thread = None
        self.polling_run = False

        manager.add_handler(confirm)

    def start(self):
        if self.method == "bot_polling":
            self.polling_auth()
            self.polling_run = True
            
            if self.polling_thread and self.polling_thread.is_alive():
                self.polling_thread.join()
            self.polling_thread = Thread(target=self.polling_listener, daemon=self.polling_daemon)
            self.polling_thread.start()
        elif self.method == "user_polling":
            pass
        elif self.method == "callback":
            pass
        self.running = True

    def stop(self):
        if self.method == "bot_polling" or self.method == "user_polling":
            self.polling_run = False
            self.polling_thread.join()
            self.polling_thread = None
        self.running = False

    def parser(self, status: int, headers: dict, body):
        messages = list()
        if body["type"] == "message_new":
            data = body["object"]
            chat = Chat(data["from_id"])
            message = Message()
            message.parse(data)
            messages.append([chat, message])
        return messages

    def responser(self, status: int, headers: dict, body: str):
        return 200, dict(), "ok"

    def send_message(self, chat, message):
        params = {"user_id": chat.id}
        if not message.text is None:
            params["message"] = message.text
        if not message.keyboard is None:
            buttons = [json.dumps([{"action": {"type": "text", "label": button.text}, "color": "default"}], ensure_ascii=False) for button in message.keyboard.buttons]
            buttons = ",".join(buttons)
            params["keyboard"] = '{"one_time":true,"buttons":[%s]}' % buttons
            params["keyboard"] = params["keyboard"]
        response = self.api_method(name="messages.send", params=params)

    def polling_listener(self):
        while self.polling_run:
            url = self.bot_url.format(server=self.polling_server, key=self.polling_key, ts=self.polling_ts,
                                      wait=self.polling_wait)
            messages = list()
            try:
                response = requests.get(url)
                data = response.json()
            except:
                time.sleep(self.polling_delay)
                logging.error("[%s] Cannot update. Code: %s. Response: %s", self.name,
                              response.status_code, response.text)
                continue
            
            updates = data.get("updates", None)
            failed = data.get("failed", None)
            if not failed is None:
                logging.warning("[%s] Get incorrect update. Code: %s. Response: %s", self.name,
                                response.status_code, response.text)
                if 2 <= failed <= 3:
                    self.polling_auth()
                time.sleep(self.polling_delay)
                continue
            self.polling_ts = data["ts"]
            
            for update in updates:
                ms = self.parser(response.status_code, response.headers, update)
                messages.extend(ms)
            for chat, message in messages:
                for handler in self.manager.handlers:
                    try:
                        handler(self, chat, message)
                    except utils.NotPassed as e:
                        continue
                    break
            time.sleep(self.polling_delay)

    def polling_auth(self):
        response = self.api_method(name="groups.getLongPollServer", params={"group_id": self.group_id})
        try:
            data = response.json()["response"]
            logging.info("[%s] Success auth. Code: %s. Response: %s", self.name, response.status_code,
                         response.text)
        except KeyError:
            logging.error("[%s] Incorrect auth response. Code: %s. Response: %s", self.name,
                          response.status_code, response.text)
        
        self.polling_key = data["key"]
        self.polling_server = data["server"]
        self.polling_ts = data["ts"]

    def api_method(self, name, params={}, method="get"):
        params["v"] = self.api_version
        params["access_token"] = self.token
        if method.lower() == "get":
            url = f"{self.api_url}/{name}?" + "&".join([f"{key}={value}" for key, value in params.items()]) 
            return requests.get(url)


@utils.only_agent(Agent)
def confirm(agent, chat, message):
    data = json.loads(message.text)
    if data["type"] == "confirmation":
        pass
    else:
        pass
    return 200, dict(), "kishkish"


class Chat(botovod.Chat):
    def __init__(self, id):
        super().__init__("botovod.agents.vk", id)


class Message(botovod.Message):
    def parse(self, data):
        self.text = data["text"]
        self.raw = data
