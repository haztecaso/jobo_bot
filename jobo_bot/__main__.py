#!/usr/bin/env python3

import logging

from .config import Config
from .bot import JoboBot
from .client import JoboClient


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="JOBO BOT")
    parser.add_argument('--prod', dest='prod', action='store_true',
            help='Production mode (testing is the default mode)')
    return parser.parse_args()


def process_events(conf:Config, events):
    bot = JoboBot(conf)
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



def main():
    args = parse_args()
    conf = Config(test = not args.prod)
    client = JoboClient(conf)
    events = client.fetch_events()
    process_events(conf, events)


if __name__ == '__main__':
    main()

__all__ = ['process_events']
