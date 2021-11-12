from typing import Union, Tuple, List
from enum import Enum, auto

from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from jobo_bot.config import Config
from jobo_bot.event import Event

SELENIUM_OPTIONS = FirefoxOptions()
SELENIUM_OPTIONS.headless = True

class FindMode(Enum):
    RAW=auto()
    BOOL=auto()
    TEXT=auto()
    NORMALIZEDTEXT=auto()
    ATTR=auto()

SELECTORS = {
        "cookie_accept_button": "div.c-mod-cookies > div > div > div > button:nth-child(2)",
        "events": "#eventsContent > div.c-mod-filter-events__event-results.row > article",
        "prev_title": "div.c-mod-card-event__data > div.c-mod-card-event__data-title",
        "prev_date": "div.c-mod-card-event__data > div.c-mod-card-event__data-date",
        "soldout": "div > div.c-mod-card-event__soldout-txt",
        "title": ".c-mod-bar-event_data-title",
        "date": ".c-mod-file-event__list-info-item-date > div:nth-child(2)",
        "duration": "li.c-mod-file-event__list-info-item.c-mod-file-event__list-info-item-time > div:nth-child(2)",
        "site": ".c-mod-bar-organization__title-text",
        "description": ".c-mod-file-event_description",
        "img": "div.c-mod-file-event__content-info__img > img",
        }

PREVIEW_SELECTORS = {
        "prev_title": FindMode.NORMALIZEDTEXT,
        "prev_date": FindMode.NORMALIZEDTEXT,
        "soldout": FindMode.BOOL,
        }

EVENT_DATA_SELECTORS = {
        "title": FindMode.NORMALIZEDTEXT,
        "date": FindMode.NORMALIZEDTEXT,
        "duration": FindMode.NORMALIZEDTEXT,
        "site": FindMode.NORMALIZEDTEXT,
        "description": FindMode.TEXT,
        "img": (FindMode.ATTR, "src"),
        }

BASE_URL   = "https://tienda.madrid-destino.com/es"
EVENTS_URL = f"{BASE_URL}/?jobo=1"


def find(parent, selector_name, mode: Union[FindMode, Tuple[FindMode, str]]):
    element = None
    result = None
    try:
        element = parent.find_element_by_css_selector(SELECTORS[selector_name])
    except NoSuchElementException:
        pass
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

def multifind(parent, selectors):
    data = {sel: find(parent, sel, mode) for sel, mode in selectors.items()}
    data["parent"] = parent
    return data

def click(driver, el):
    try:
        el.click()
    except ElementClickInterceptedException:
        webdriver.ActionChains(driver).move_to_element(el).click(el).perform()

def accept_cookies(driver):
    driver.get(EVENTS_URL)
    button = find(driver, "cookie_accept_button", FindMode.RAW)
    if button:
        click(driver, button)

def get_elems_preview(driver):
    driver.get(EVENTS_URL)
    elems = driver.find_elements_by_css_selector(SELECTORS["events"])
    preview_list = [multifind(ev, PREVIEW_SELECTORS) for ev in elems]
    return list(filter(lambda ev: not ev["soldout"], preview_list))

def scrape_event(config, driver):
    WebDriverWait(driver, 15)\
            .until(EC.presence_of_element_located(
                (By.CSS_SELECTOR, SELECTORS["title"])
                ))
    event_data = multifind(driver, EVENT_DATA_SELECTORS)
    event_data["info_url"] = driver.current_url
    event_data["buy_url"] = driver.current_url
    del event_data["parent"]
    return Event(config.db, **event_data)

def parse_events(config, driver):
    visited_events = []
    events = []
    while True:
        previews = get_elems_preview(driver)
        try:
            event_preview = next(ev for ev in previews if (ev["prev_title"],ev["prev_date"]) not in visited_events)
        except StopIteration:
            break
        config.logger.debug(f"- Parsing {event_preview['prev_title']}")
        visited_events.append((event_preview["prev_title"], event_preview["prev_date"]))
        click(driver, event_preview["parent"]) #TODO: FIX
        event = scrape_event(config, driver)
        events.append(event)
        break
    return events

def scrape_events(config):
    driver = webdriver.Firefox(options=SELENIUM_OPTIONS)
    config.logger.debug("Accepting cookies")
    accept_cookies(driver)
    config.logger.debug("Fetching events")
    events = parse_events(config, driver)
    driver.quit()
    return events

