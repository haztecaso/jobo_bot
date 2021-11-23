#!/usr/bin/env python3

import json

from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sys import argv

Base = declarative_base()

def create_session(origin_db_filename):
    return Session()

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

keys_map = {
        "title": "title",
        "date" : "date",
        "duration" : "duration",
        "place" : "site",
        "img_url" : "img",
        "buy_url" : "buy_url",
        "info_url" : "info_url",
        "message_id" : "message_id",
        }

if __name__ == '__main__':
    if len(argv) > 1:
        origin_db_filename = argv[1]
        name = origin_db_filename.split(".")[0]
        new_engine = create_engine(f'sqlite:///{name}_migration_01.db')
        Session = sessionmaker(bind=new_engine)
        new_session = create_session(origin_db_filename)
        Base.metadata.create_all(new_engine)
        with open(origin_db_filename) as origin_db_file:
            origin_data = json.load(origin_db_file)
        for old_data in origin_data["_default"].values():
            data = {}
            for new_key, old_key in keys_map.items():
                if old_key in old_data and old_data[old_key] != []:
                    data[new_key] = old_data[old_key]
            event = Event(**data)
            new_session.add(event)
        new_session.commit()
    else:
        print("missing required argument: origin database path")
