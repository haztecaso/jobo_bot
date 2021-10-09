import logging, requests
from typing import List, Optional

from bs4 import BeautifulSoup 
from jobo_bot.config import Config
from jobo_bot.event import Event


BASE_URL   = "https://madridcultura-jobo.shop.secutix.com"
LOGIN_URL  = f"{BASE_URL}/account/login"
EVENTS_URL = f"{BASE_URL}/secured/list/events"


class EventScraper:
    def __init__(self, conf: Config):
        self.config = conf
        self.event: Optional[Event] = None
        self._soup = None

    def scrape(self, soup) -> Event:
        self._soup = soup
        event = Event(
                self.config.db,
                id = self._scrape_id(),
                title = self._scrape_title(),
                space = self._scrape_space(),
                site = self._scrape_site(),
                date = self._scrape_date(),
                img = self._scrape_img(),
                info_url = self._scrape_info_url(),
                buy_url = self._scrape_buy_url(),
                )
        self.config.logger.debug(f"Scraped event: {event}")
        return event

    def _scrape_selector(self, selector):
        result = self._soup.select(selector)
        if result:
            result = result[0].text
            result = result.replace('\n','').replace('\r','')
            result = ' '.join(result.split())
        return result

    def _scrape_attribute(self, selector, attribute):
        result = self._soup.select(selector)
        if result:
            result = result[0].get(attribute)
        return result

    def _scrape_href(self, selector):
        return self._scrape_attribute(selector, 'href')

    def _scrape_id(self):
        return self._soup.get('id').replace('prod_','')
 
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


class Scraper():
    def __init__(self, config:Config):
        self.config = config
        self.username = config.jobo_user
        self.password = config.jobo_password 
        self.session = requests.session()
        self.logger = config.logger
        self._token = None
        self.login()

    def get_token(self):
        self.logger.debug("Getting csrf token")
        result = self.session.get(LOGIN_URL)
        soup = BeautifulSoup(result.text, 'html.parser')
        return soup.find('input', {'name': '_csrf'}).get('value')

    @property
    def token(self):
        if not self._token:
            self._token = self.get_token()
        return self._token

    def login(self):
        self.logger.debug("logging in")
        payload = {
                'login': self.username,
                'password': self.password,
                '_rememberThisLogin': 'on',
                '_csrf': self.token
                }
        return self.session.post(
                LOGIN_URL,
                data=payload,
                headers=dict(referer=LOGIN_URL)
                )

    def _get_events_raw(self):
        self.logger.debug("Getting events")
        return self.session.get(
                EVENTS_URL,
                headers = dict(referer=EVENTS_URL)
                ).text

    def fetch_events(self) -> List[Event]:
        html = self._get_events_raw()
        self.logger.debug("Scraping events")
        soup = BeautifulSoup(html, 'html.parser')
        events_raw = soup.select('div.group_content > ul > li > .product')
        self.logger.debug(f"{len(events_raw)} events found")
        return [EventScraper(self.config).scrape(event_raw)\
                for event_raw in events_raw]

