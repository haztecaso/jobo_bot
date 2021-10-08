import urllib.parse

from tinydb import TinyDB, Query

from .config import Config


class Event:
    def __init__(self, db:TinyDB,  **data):
        self.db = db
        self.data = data
        self.sent = False

    def db_search(self):
        result = self.db.search(
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
        if not self.db_search():
            self.db.insert(self.data)

    def db_update(self):
        self.db.update(self.data,
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
        del self.data['message_id']
    
    def __repr__(self):
        return f"{self.get('title')} - {self.get('date')}"

    def __hash__(self):
        return hash(str(self)+self.get('date'))

    def message(self):
        message  = f"*{self.get('title', True)}* \\- "
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
            message += f"en [madridcultura\\.es]({url}) o "
            url  = "https://duckduckgo.com/?q="
            url += urllib.parse.quote(f"{self.get('title')} - {self.get('site')}")
            message  += f"en [duckduckgo\\.com]({url})"
        return message

    def _message_buy(self):
        url = self.get('buy_url')
        return f"[Consigue tu entrada]({url})" if url else "*¡Entradas agotadas\\!*"


class EventScraper:
    def __init__(self, conf:Config,  event_soup):
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
