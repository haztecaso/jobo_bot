#!/usr/bin/env python3
"""
TODO
- Gestión de errores: Logs, Probar a enviar de nuevo eventos no enviados
- Backups del historial
- Limpiar y refactorizar código
- Editar mensajes cuando se agotan las entradas
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

TESTING = True

BASE_URL   = "https://madridcultura-jobo.shop.secutix.com"
LOGIN_URL  = f"{BASE_URL}/account/login"
EVENTS_URL = f"{BASE_URL}/secured/list/events"

JOBO_USER  = "adrianlattes@gmail.com"
JOBO_PASS  = "jF%3L9j$0e7#dbbe?7]*BN5Cy"

BOT_TOKEN = "1749715587:AAH626inXY9mDxNHYiiIII8Rz5RoYBhgsrM"
CHAT_ID_TEST = "1624473"
CHAT_ID_PROD = "-1001391859850"

MSG_COUNT = 0

def clean(string):
    string = string.replace('\n', '').replace('\r', '').split()
    string = ' '.join(string)
    return string


def get_token():
    logging.debug("getting csrf token")
    session = requests.session()
    result = session.get(LOGIN_URL)
    soup = BeautifulSoup(result.text, 'html.parser')
    token = soup.find('input', {'name': '_csrf'}).get('value')
    return (token, session)


def login(username:str, password:str):
    token, session = get_token()
    logging.debug("logging in")
    payload = {
            'login': username,
            'password': password,
            '_rememberThisLogin': 'on',
            '_csrf': token
            }
    result = session.post(LOGIN_URL, data=payload, headers=dict(referer=LOGIN_URL))
    return (result, session)


def select_event(event, selector):
    return clean(event.select(selector)[0].text)


def scrape_event(event):
    title = select_event(event, '.title')
    space = select_event(event, '.location .space')
    site = select_event(event, '.location .site')
    date = None

    if event.select('.date .unique'):
        date = select_event(event, '.date .unique')
    elif event.select('.date .range'):
        date = select_event(event, '.date .range')

    img = None
    if event.select('img'):
        img = event.select('img')[0].get('data-img-large')

    info_url = None
    if event.select('.more_info a'):
        info_url = event.select('.more_info a')[0].get('href')

    buy_url = None
    if event.select('span.button a'):
        buy_url = BASE_URL+event.select('span.button a')[0].get('href')
    return {
            'title'      : title,
            'space'      : space,
            'site'       : site,
            'date'       : date,
            'img'        : img,
            'info_url'   : info_url,
            'buy_url'    : buy_url,
            'sent'       : False,
            'added_time' : time(),
            'hash'       : hash(title+space+site+date)
            }


def scrape_events(session):
    logging.debug("scraping events")
    result = session.get(EVENTS_URL, headers = dict(referer = EVENTS_URL))
    soup = BeautifulSoup(result.text, 'html.parser')
    events = []
    for ev in soup.select('div.group_content > ul > li > div.product'):
        logging.debug(f"scraping event nº{len(events)}")
        events.append(scrape_event(ev))
    return events


def esc(message):
    for char in "_*[]()~`>#+-=|{}.!":
        message = message.replace(char, '\\'+char)
    return message


def markdown_message(event):
    message  = f"*{esc(event['title'])}* \- {esc(event['site'])}\n"
    message += f"_{esc(event['date'])}_\n"
    if event['info_url']:
        message += f"[Más información]({event['info_url']})\n"
    else:
        info_url  = "https://www.madridcultura.es/resultado/filtro?&texto="
        info_url += urllib.parse.quote(f"{event['title']}")
        message  += f"Buscar información: en [madridcultura\.es]({info_url}) o "
        info_url  = "https://duckduckgo.com/?q="
        info_url += urllib.parse.quote(f"{event['title']} - {event['site']}")
        message  += f"en [duckduckgo\.com]({info_url})\n"
    if event['buy_url']:
        message += f"[Consigue tu entrada]({event['buy_url']})"
    else:
        message += f"*¡Entradas agotadas\!*"
    return message
    

def notify(bot, event, chat_id):
    # See telegram comments on message limits:
    # https://core.telegram.org/bots/faq#my-bot-is-hitting-limits-how-do-i-avoid-this
    global MSG_COUNT
    message = markdown_message(event)
    try:
        if event['img']:
            bot.send_photo(
                    chat_id=chat_id,
                    photo=event['img'],
                    parse_mode=telegram.ParseMode.MARKDOWN_V2,
                    caption=message
                    )
        else:
            bot.send_message(
                    chat_id=chat_id,
                    parse_mode=telegram.ParseMode.MARKDOWN_V2,
                    text = message
                    )
    except Exception as e:
        print(e)
        return False
    else:
        sleep(1.1) # Avoid sending more than one message per second
        MSG_COUNT += 1
        if MSG_COUNT % 20 == 0:
            sleep(40) # Avoid sending more than 20 messages per minute
        return True

def register_new(event, db, bot, chat_id):
    logging.info(f"New event: {event['title']} - {event['site']}")
    event['sent'] = notify(bot, event, chat_id)
    db.insert(event)


def update_old(event, db, bot, chat_id):
    #TODO: implementar
    pass


def main(**kwargs):
    if kwargs['testing']:
        logging.debug(f"Running in testing mode")
    else:
        logging.debug(f"Running in production mode")
    db, query = TinyDB('jobo_history.json'), Query()
    result, session = login(JOBO_USER, JOBO_PASS)
    events = scrape_events(session)
    chat_id = CHAT_ID_TEST if kwargs['testing'] else CHAT_ID_PROD
    bot = telegram.Bot(token=BOT_TOKEN)
    for event in events:
        if db.search(query.title == event['title']): #TODO: falla en el servidor
            update_old(event, db, bot, chat_id)
        else:
            register_new(event, db, bot, chat_id)

def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="JOBO BOT")
    parser.add_argument('--prod', dest='prod', action='store_true',
            help='Production mode (testing is the default mode)')
    parser.add_argument('--debug', dest='debug', action='store_true',
            help='Set log level to DEBUG')
    return parser.parse_args()

if __name__ == '__main__':
    try:
        args = parse_args()
        logging.basicConfig(
            format = '%(asctime)s:%(levelname)s:%(process)d:%(message)s',
            level = logging.DEBUG if args.debug else logging.INFO,
            handlers = [logging.FileHandler("jobo_bot.log"), logging.StreamHandler(sys.stdout)]
            )
        main(testing = not args.prod)
    except Exception as e:
        logging.error(''.join(traceback.format_exception(None, e, e.__traceback__)))
