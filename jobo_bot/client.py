import logging, requests

from bs4 import BeautifulSoup 
from .config import Config
from .eventscraper import EventScraper

class JoboClient():
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
        result = self.session.get(Config.LOGIN_URL)
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
                Config.LOGIN_URL,
                data=payload,
                headers=dict(referer=Config.LOGIN_URL)
                )

    def _get_events_raw(self):
        self.logger.debug("Getting events")
        return self.session.get(
                Config.EVENTS_URL,
                headers = dict(referer=Config.EVENTS_URL)
                ).text

    def fetch_events(self):
        html = self._get_events_raw()
        self.logger.debug("Scraping events")
        soup = BeautifulSoup(html, 'html.parser')
        events = []
        events_raw = soup.select('div.group_content > ul > li > .product')
        self.logger.debug(f"{len(events_raw)} events found")
        for event_raw in events_raw:
            event = EventScraper(self.config, event_raw).event
            self.logger.debug(f"Scraped event: {event}")
            events.append(event)
        return events
