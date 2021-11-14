#!/usr/bin/env python3

import logging

from .config import Config
from jobo_bot.bot import JoboBot

from jobo_bot.scrapers.secutix import Scraper as SecutixScraper
from jobo_bot.scrapers.madriddestino import scrape_events as MadridDestinoScraper 


def parse_args():
    import argparse
    parser = argparse.ArgumentParser(description="JOBO BOT")
    parser.add_argument('--prod', dest='prod', action='store_true',
            help='Production mode (testing is the default mode)')
    return parser.parse_args()


def process_secutix_events(conf:Config, events):
    bot = JoboBot(conf)
    for event in events:
        entradas_disponibles = bool(event.data['buy_url'])
        if (not event.sent) and (not event.db_search()) and entradas_disponibles:
            logging.info(f"New event: {event}")
            bot.notify_new_event(event)
            event.db_insert()

def process_madriddestino_events(conf:Config, events):
    bot = JoboBot(conf)
    for event in events:
        if (not event.sent) and (not event.db_search()):
            logging.info(f"New event: {event}")
            bot.notify_new_event(event)
            event.db_insert()

def main():
    args = parse_args()
    conf = Config(test = not args.prod)
    events = MadridDestinoScraper(conf)
    process_madriddestino_events(conf, events)
    events = SecutixScraper(conf).fetch_events()
    process_secutix_events(conf, events)

if __name__ == '__main__':
    main()
