#!/usr/bin/env python3
"""
TODO
- Probar a enviar de nuevo eventos no enviados
- Backups del historial
- Versión con retraso
- Base de datos con sqlite
- Escalar imágenes para que estén todas al mismo tamaño
- Configuración: fichero / argumentos
"""

import logging, sys, traceback
import urllib.parse
from time import time, sleep

import requests
from bs4 import BeautifulSoup
from tinydb import TinyDB, Query
import telegram
from telegram.utils.helpers import escape_markdown

logging.getLogger('telegram').setLevel(logging.WARNING)

LOGGING_FORMAT = '%(asctime)s:%(levelname)s:%(process)d:%(message)s'

BASE_URL   = "https://madridcultura-jobo.shop.secutix.com"
LOGIN_URL  = f"{BASE_URL}/account/login"
EVENTS_URL = f"{BASE_URL}/secured/list/events"

JOBO_USER  = "adrianlattes@gmail.com"
JOBO_PASS  = "jF%3L9j$0e7#dbbe?7]*BN5Cy"

BOT_TOKEN = "1749715587:AAH626inXY9mDxNHYiiIII8Rz5RoYBhgsrM"
CHAT_ID_TEST = "1624473"
CHAT_ID_PROD = "-1001391859850"

DB = TinyDB('database.json')

MSG_COUNT = 0


class JoboClient():
    def __init__(self, username:str, password: str):
        self.username = username
        self.password = password
        self.session = requests.session()
        self.token = None
        self.login()

    def get_token(self):
        logging.debug("Getting csrf token")
        result = self.session.get(LOGIN_URL)
        soup = BeautifulSoup(result.text, 'html.parser')
        self.token = soup.find('input', {'name': '_csrf'}).get('value')

    def login(self):
        if not self.token:
            self.get_token()
        logging.debug("Logging in")
        payload = {
                'login': self.username,
                'password': self.password,
                '_rememberThisLogin': 'on',
                '_csrf': self.token
                }
        result = self.session.post(LOGIN_URL, data=payload, headers=dict(referer=LOGIN_URL))

    def get_events_raw(self):
        logging.debug("Getting events")
        return self.session.get(EVENTS_URL, headers = dict(referer=EVENTS_URL)).text


class Event:
    def __init__(self, **data):
        self.data = data
        self.sent = False


    def db_search(self):
        global DB
        result = DB.search(
                (Query().title == self.get('title'))
                & (Query().date == self.get('date'))
                )
        return result[0] if result else result

    def db_diff(self):
        db_result = self.db_search()
        if 'message_id' in db_result:
            del db_result['message_id']
        return not self.data == dict(db_result)

    def db_insert(self):
        global DB
        if not self.db_search():
            DB.insert(self.data)

    def db_update(self):
        global DB
        DB.update(self.data,
                (Query().title == self.get('title'))
                & (Query().date == self.get('date'))
                )

    def get(self, key, escape_markdown = False):
        value = self.data[key]
        if escape_markdown:
            for char in "_*[]()~`>#+-=|{}.!":
                value = value.replace(char, '\\'+char)
        return value

    @property
    def message_id(self):
        if 'message_id' in self.data:
            return self.data['message_id']
        else:
            message_id = dict(self.db_search()).get('message_id', None)
            if message_id:
                self.data['message_id'] = message_id
            return message_id

    @message_id.setter
    def message_id(self, message_id):
        self.data['message_id'] = message_id

    @message_id.deleter
    def message_id(self):
        del data['message_id']
    
    def __repr__(self):
        return f"{self.get('title')} - {self.get('date')}"

    def __hash__(self):
        return hash(str(self)+self.get('date'))

    def message(self):
        message  = f"*{self.get('title', True)}* \- "
        message += f"{self.get('site', True)}\n"
        message += f"_{self.get('date', True)}_\n"
        message += self._message_info() + "\n"
        message += self._message_buy()
        return message

    def _message_info(self):
        url = self.get('info_url')
        if url:
            message = f"[Más información]({url})"
        else:
            message  = "Buscar información "
            url  = "https://www.madridcultura.es/resultado/filtro?&texto="
            url += urllib.parse.quote(f"{self.get('title')}")
            message += f"en [madridcultura\.es]({url}) o "
            url  = "https://duckduckgo.com/?q="
            url += urllib.parse.quote(f"{self.get('title')} - {self.get('site')}")
            message  += f"en [duckduckgo\.com]({url})"
        return message

    def _message_buy(self):
        url = self.get('buy_url')
        return f"[Consigue tu entrada]({url})" if url else "*¡Entradas agotadas\!*"


class EventScraper:
    def __init__(self, event_soup):
        self.soup = event_soup
        self.event = None
        self.scrape()

    def scrape(self):
        self.event = Event(
                id = self._scrape_id(),
                title = self._scrape_title(),
                space = self._scrape_space(),
                site = self._scrape_site(),
                date = self._scrape_date(),
                img = self._scrape_img(),
                info_url = self._scrape_info_url(),
                buy_url = self._scrape_buy_url(),
                )

    def _scrape_selector(self, selector):
        result = self.soup.select(selector)
        if result:
            result = result[0].text
            result = result.replace('\n','').replace('\r','')
            result = ' '.join(result.split())
        return result

    def _scrape_attribute(self, selector, attribute):
        result = self.soup.select(selector)
        if result:
            result = result[0].get(attribute)
        return result

    def _scrape_href(self, selector):
        return self._scrape_attribute(selector, 'href')

    def _scrape_id(self):
        return self.soup.get('id').replace('prod_','')
 
    def _scrape_title(self):
        return self._scrape_selector('.title')

    def _scrape_space(self):
        return self._scrape_selector('.location .space')

    def _scrape_site(self):
        return self._scrape_selector('.location .site')

    def _scrape_date(self):
        date = self._scrape_selector('.date .unique')
        if not date:
            date = self._scrape_selector('.date .range')
        return date

    def _scrape_img(self):
        return self._scrape_attribute('img', 'data-img-large')

    def _scrape_info_url(self):
        return self._scrape_href('.more_info a')

    def _scrape_buy_url(self):
        rel_url = self._scrape_href('span.button a')
        url = BASE_URL+str(rel_url) if rel_url else None
        return url


def scrape_events(html:str):
    soup = BeautifulSoup(html, 'html.parser')
    events = []
    events_raw = soup.select('div.group_content > ul > li > div.product')
    logging.debug(f"{len(events_raw)} events found")
    for event_raw in events_raw:
        event = EventScraper(event_raw).event
        logging.debug(f"Scraped event: {event}")
        events.append(event)
    return events


class JoboBot():
    def __init__(self, token, chat_id):
        self.token = token
        self.chat_id = chat_id
        self.bot = telegram.Bot(token=self.token)
        self.msg_count = 0

    def notify_new_event(self, event:Event):
        # See telegram comments on message limits:
        # https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
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
            sleep(1.05) # Avoid sending more than one message per second
            self.msg_count += 1
            if self.msg_count % 20 == 0:
                sleep(40) # Avoid sending more than one message per minute

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
            logging.debug(f"Message {event.message_id} didn't change")
        except Exception as e:
            raise e
        else:
            logging.info(f"Message {event.message_id} updated")
            sleep(1.05) # Avoid sending more than one message per second
            self.msg_count += 1
            if self.msg_count % 20 == 0:
                sleep(40) # Avoid sending more than one message per minute


def fetch_events():
    client = JoboClient(JOBO_USER, JOBO_PASS)
    events_raw = client.get_events_raw()
    events = scrape_events(events_raw)
    return events


def process_events(events, chat_id):
    bot = JoboBot(BOT_TOKEN, chat_id)
    news = False
    for event in events:
        entradas_disponibles = bool(event.data['buy_url'])
        if (not event.sent) and (not event.db_search()) and entradas_disponibles:
            news = True
            logging.info(f"New event: {event}")
            bot.notify_new_event(event)
            event.db_insert()
        elif event.db_search() and event.db_diff():
            news = True
            logging.info(f"Event changed: {event}")
            event.data['buy_url'] = None
            if event.message_id:
                bot.update_event_info(event)
            event.db_update()
    if not news:
        logging.debug("Didn't find any new events or changes")


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="JOBO BOT")
    parser.add_argument('--prod', dest='prod', action='store_true',
            help='Production mode (testing is the default mode)')
    parser.add_argument('--debug', dest='debug', action='store_true',
            help='Set log level to DEBUG')
    return parser.parse_args()


def main():
    args = parse_args()
    try:
        if args.debug:
            logging.basicConfig(
                    format = LOGGING_FORMAT, level = logging.DEBUG,
                    handlers = [
                        logging.FileHandler("jobo_bot.debug.log"),
                        logging.StreamHandler(sys.stdout)
                        ]
                    )
        else:
            logging.basicConfig(
                    format = LOGGING_FORMAT, level = logging.INFO,
                    handlers = [
                        logging.FileHandler("jobo_bot.log"),
                        logging.StreamHandler(sys.stdout)
                        ]
                    )
    except Exception as e:
        logging.error(''.join(traceback.format_exception(None, e, e.__traceback__)))
    else:
        testing = not args.prod
        if testing:
            logging.debug(f"Running in testing mode")
        else:
            logging.debug(f"Running in production mode")
        chat_id = CHAT_ID_TEST if testing else CHAT_ID_PROD
        process_events(fetch_events(), chat_id)


if __name__ == '__main__':
    main()
