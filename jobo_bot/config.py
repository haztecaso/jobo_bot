import logging, sys, json
from tinydb import TinyDB, Query

class Config():

    BASE_URL   = "https://madridcultura-jobo.shop.secutix.com"
    LOGIN_URL  = f"{BASE_URL}/account/login"
    EVENTS_URL = f"{BASE_URL}/secured/list/events"

    def __init__(self, **kwargs):
        self.test = kwargs.get('test', True)
        self.file = kwargs.get('file', 'config.test.json' if self.test else 'config.json')
        with open(self.file) as f:
            self.data = json.load(f)
        self.logger = logging.getLogger("jobo_bot")
        self.config_logger(self.logging_format, self.test)
        self._db = None

    def _get(self, key):
        if key not in self.data:
            raise KeyError(f'Missing key "{key}" in config file {self.file}')
        return self.data[key]

    @property
    def db_file(self): return self.data.get('db_file', 'database.json')

    @property
    def db(self):
        if not self._db:
            self._db = TinyDB(self.db_file)
        return self._db

    @property
    def logging_format(self):
        return self.data.get(
                'logging_format',
                '%(asctime)s:%(levelname)s:%(process)d:%(message)s'
                )

    @property
    def jobo_user(self): return self._get('jobo_user')

    @property
    def jobo_password(self): return self._get('jobo_password')

    @property
    def telegram_bot_token(self): return self._get('telegram_bot_token')

    @property
    def telegram_chat_id(self): return self._get('telegram_chat_id')

    @staticmethod
    def config_logger(format:str, test:bool):
        logging.getLogger('telegram').setLevel(logging.WARNING)
        logger = logging.getLogger("jobo_bot")
        logger.setLevel(logging.DEBUG if test else logging.INFO)
        formatter = logging.Formatter(format)
        log_file = 'jobo_bot.test.log' if test else 'jobo_bot.log' 
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)
