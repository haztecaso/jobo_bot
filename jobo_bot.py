#!/usr/bin/env python3
import argparse, logging, json
import telegram

from enum import Enum, auto
from typing import Union, Tuple, List

from os.path import isfile
import sys
from time import sleep

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

parser = argparse.ArgumentParser(description="JOBO BOT")
parser.add_argument('--prod', dest='prod', action='store_true',
        help='Production mode (testing is the default mode)')
args = parser.parse_args()

test = not args.prod
config_file = 'config.json' if args.prod else 'config.test.json'

conf = None
with open(config_file) as f:
    conf = json.load(f)

logger = logging.getLogger("jobo_bot")

def config_logger(logger):
    logger.setLevel(logging.DEBUG if test else logging.INFO)
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(process)d:%(message)s')
    log_file = 'jobo_bot.test.log' if test else 'jobo_bot.log'

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

Base = declarative_base()

def escape_md(text:str):
    return text.replace(".", "\\.")\
               .replace("-", "\\-")

class Event(Base):
    __tablename__ = 'events'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    date = Column(String)
    duration = Column(String)
    place = Column(String)
    info_url = Column(String)
    buy_url = Column(String)
    img_url = Column(String)
    message_id = Column(String)

    def __repr__(self):
        return f"<Event id='{self.id}' title='{self.title}' date='{self.date}' message_id='{self.message_id}'>"

    @property
    def message_md(self):
        message = f"*{self.title}*"
        if self.place:
            message += f" - {self.place}"
        message += "\n"
        message += f"_{self.date}_\n"
        if self.info_url:
            if self.info_url == self.buy_url:
                message += f"[Mas información / Comprar entradas]({self.info_url})."
            else:
                message += f"[Mas información]({self.info_url})"
        if self.buy_url and self.buy_url != self.info_url:
            if self.info_url:
                message += ". "
            message += f"[Comprar entradas]({self.buy_url})."
        if self.info_url or self.buy_url:
            message += "\n"
        return escape_md(message)

def get_event(session, title, date):
    return session\
            .query(Event)\
            .order_by(Event.id.desc())\
            .filter(Event.title == title, Event.date == date).first()

def get_or_create_event(session, data):
    event = get_event(session, data["title"], data["date"])
    if not event:
        event = Event(**data)
    return event

msg_send_count = 0

def wait_send():
    global msg_send_count
    sleep(1.05)
    msg_send_count += 1
    if msg_send_count % 20 == 0:
        sleep(40) # Avoid sending more than 20 messages per minute

def notify_new_event(event: Event):
    bot = telegram.Bot(token=conf["telegram_bot_token"])
    kwargs = {
            "chat_id": conf["telegram_chat_id"],
            "parse_mode": telegram.ParseMode.MARKDOWN_V2,
            "caption" if event.img_url else "text": event.message_md,
            }
    message = None
    try:
        message = bot.send_photo(photo = event.img_url, **kwargs)\
                        if event.img_url\
                        else bot.send_message(**kwargs)
    except telegram.error.BadRequest as e:
        print(e)
        pass #TODO
    else:
        event.message_id = message.message_id
        logger.info(f"Message sent: {event}")
        wait_send()

def update_event_info(event):
    #TODO: use and test this function
    global msg_send_count
    bot = telegram.Bot(token=conf["telegram_bot_token"])
    assert event.message_id is not None
    kwargs = {
            "chat_id": conf["telegram_chat_id"],
            "message_id": event.message_id,
            "parse_mode": telegram.ParseMode.MARKDOWN_V2,
            "caption" if event.img_url else "text": event.message_md,
            }
    try:
        bot.edit_message_caption(photo = event.img_url, **kwargs)\
                        if event.img_url\
                        else bot.edit_message_text(**kwargs)
    except telegram.error.BadRequest:
        pass #TODO
    else:
        wait_send()

class FindMode(Enum):
    RAW=auto()
    BOOL=auto()
    TEXT=auto()
    NORMALIZEDTEXT=auto()
    ATTR=auto()

SELENIUM_OPTIONS = FirefoxOptions()
SELENIUM_OPTIONS.headless = True

MD_SELECTORS = {
        "cookie_accept_button": "div.c-mod-cookies > div > div > div > button:nth-child(2)",
        "events": "#eventsContent > div.c-mod-filter-events__event-results.row > article",
        "prev_title": "div.c-mod-card-event__data > div.c-mod-card-event__data-title",
        "prev_date": "div.c-mod-card-event__data > div.c-mod-card-event__data-date",
        "soldout": "div > div.c-mod-card-event__soldout-txt",
        "title": ".c-mod-bar-event_data-title",
        "date": ".c-mod-file-event__list-info-item-date > div:nth-child(2), .c-mod-file-event__list-info-item-date2 > div:nth-child(2)",
        "duration": "li.c-mod-file-event__list-info-item.c-mod-file-event__list-info-item-time > div:nth-child(2)",
        "place": ".c-mod-bar-organization__title-text",
        "description": ".c-mod-file-event_description",
        "img_url": "div.c-mod-file-event__content-info__img > img",
        }

MD_PREVIEW_SELECTORS = {
        "prev_title": FindMode.NORMALIZEDTEXT,
        "prev_date": FindMode.NORMALIZEDTEXT,
        "soldout": FindMode.BOOL,
        }

MD_EVENT_DATA_SELECTORS = {
        "title": FindMode.NORMALIZEDTEXT,
        "date": FindMode.NORMALIZEDTEXT,
        "duration": FindMode.NORMALIZEDTEXT,
        "place": FindMode.NORMALIZEDTEXT,
        "img_url": (FindMode.ATTR, "src"),
        # "description": FindMode.TEXT,
        }

MD_BASE_URL   = "https://tienda.madrid-destino.com/es"
MD_EVENTS_URL = f"{MD_BASE_URL}/?jobo=1"

def selenium_find(parent, selector):
    element = None
    try: element = parent.find_element_by_css_selector(selector)
    except NoSuchElementException: pass
    return element

def selenium_wait(driver, selector_name, timeout = 15):
    WebDriverWait(driver, timeout)\
            .until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, MD_SELECTORS[selector_name])
                ))

def selenium_click(driver, el):
    try:
        el.click()
    except ElementClickInterceptedException:
        webdriver.ActionChains(driver).move_to_element(el).click(el).perform()

def find_selector(parent, selector_name, mode: Union[FindMode, Tuple[FindMode, str]] = FindMode.RAW):
    element = selenium_find(parent, MD_SELECTORS[selector_name])
    result = None
    if mode == FindMode.RAW:
        result = element
    elif mode == FindMode.BOOL:
        result = True if element else False
    elif mode == FindMode.TEXT:
        result = element.text if element else element
    if mode == FindMode.NORMALIZEDTEXT:
        result = element.text.replace('\n', ' ') if element else element
    elif isinstance(mode,tuple) and mode[0] == FindMode.ATTR:
        assert len(mode) == 2 and isinstance(mode[1], str), "mode should be of form (FindMode.ATTR, str)"
        result = element.get_attribute(mode[1]) if element else element
    return result

def find_selectors(parent, selectors_with_modes):
    data = {sel: find_selector(parent, sel, mode) for sel, mode in selectors_with_modes.items()}
    data["parent"] = parent
    return data

def md_accept_cookies(driver):
    driver.get(MD_EVENTS_URL)
    button = find_selector(driver, "cookie_accept_button", FindMode.RAW)
    if button:
        selenium_click(driver, button)

def md_get_elems_preview(driver):
    driver.get(MD_EVENTS_URL)
    elems = driver.find_elements_by_css_selector(MD_SELECTORS["events"])
    preview_list = [find_selectors(ev, MD_PREVIEW_SELECTORS) for ev in elems]
    return list(filter(lambda ev: not ev["soldout"], preview_list))

def md_scrape_event(session, driver):
    selenium_wait(driver, "title")
    event_data = find_selectors(driver, MD_EVENT_DATA_SELECTORS)
    event_data["info_url"] = driver.current_url
    event_data["buy_url"] = driver.current_url
    del event_data["parent"]
    event = get_or_create_event(session, event_data)
    session.add(event)
    logger.debug(f"Scraped event: {event}")
    return event

def md_parse_events(session, driver):
    visited_events = []
    events = []
    while True:
        previews = md_get_elems_preview(driver)
        try:
            event_preview = next(ev for ev in previews if (ev["prev_title"],ev["prev_date"]) not in visited_events)
        except StopIteration:
            break
        visited_events.append((event_preview["prev_title"], event_preview["prev_date"]))
        selenium_click(driver, event_preview["parent"]) #TODO: FIX
        event = md_scrape_event(session, driver)
        events.append(event)
    return events

def MadridDestinoScraper(session):
    driver = webdriver.Firefox(options=SELENIUM_OPTIONS)
    logger.debug("Accepting cookies")
    md_accept_cookies(driver)
    logger.debug("Scraping madrid-destino.com events")
    events = md_parse_events(session, driver)
    driver.quit()
    return events

def process_events(session, events: List[Event]):
    for event in events:
        if not event.message_id:
            notify_new_event(event)
            session.commit()

config_logger(logger)
engine = create_engine(f'sqlite:///{conf["db_file"]}')
Session = sessionmaker(bind=engine)

if __name__ == '__main__':
    if not isfile(conf["db_file"]):
        logger.info(f"Creating db file: ./{conf['db_file']}")
        Base.metadata.create_all(engine)
    session = Session()
    # e = Event(title="Prueba", date="today", info_url="url1", buy_url="url2")
    # session.add(e)
    # session.commit()
    # e = get_event(session, "Prueba", "today")
    events = MadridDestinoScraper(session)
    session.commit()
    process_events(session, events)
    # notify_new_event()
