from .config import Config
from .event import Event

class EventScraper:
    def __init__(self, conf:Config, event_soup):
        self.config = conf
        self.soup = event_soup
        self.event = None
        self.scrape()

    def scrape(self):
        self.event = Event(
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
        url = Config.BASE_URL+str(rel_url) if rel_url else None
        return url
