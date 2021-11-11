from .config import Config
from .event import Event

from time import sleep

import telegram

class JoboBot():
    def __init__(self, config:Config):
        self.token = config.telegram_bot_token
        self.chat_id = config.telegram_chat_id
        self.logger = config.logger
        self.bot = telegram.Bot(token=self.token)
        self.msg_count = 0

    def notify_new_event(self, event:Event):
        photo = event.get('img')
        message_id = None
        try:
            if photo:
                message_id = self.bot.send_photo(
                        chat_id = self.chat_id,
                        parse_mode = telegram.ParseMode.MARKDOWN_V2,
                        photo = photo,
                        caption = event.message()
                        ).message_id
            else:
                message_id = self.bot.send_message(
                        chat_id = self.chat_id,
                        parse_mode = telegram.ParseMode.MARKDOWN_V2,
                        text = event.message()
                        ).message_id
        except Exception as e:
            raise e
        else:
            event.sent = True
            event.message_id = message_id
            # See telegram comments on message limits:
            # https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
            sleep(1.05) # Avoid sending more than one message per second
            self.msg_count += 1
            if self.msg_count % 20 == 0:
                sleep(40) # Avoid sending more than 20 messages per minute

    def update_event_info(self, event:Event):
        photo = event.get('img')
        try:
            if photo:
                self.bot.edit_message_caption(
                        chat_id = self.chat_id,
                        message_id = event.message_id,
                        parse_mode = telegram.ParseMode.MARKDOWN_V2,
                        photo = photo,
                        caption = event.message()
                        )
            else:
                self.bot.edit_message_text(
                        chat_id = self.chat_id,
                        message_id = event.message_id,
                        parse_mode = telegram.ParseMode.MARKDOWN_V2,
                        text = event.message()
                        )
        except telegram.error.BadRequest as e:
            self.logger.debug(f"Message {event.message_id} didn't change")
        except Exception as e:
            raise e
        else:
            self.logger.info(f"Message {event.message_id} updated")
            sleep(1.05) # Avoid sending more than one message per second
            self.msg_count += 1
            if self.msg_count % 20 == 0:
                sleep(40) # Avoid sending more than one message per minute
