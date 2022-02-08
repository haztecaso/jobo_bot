#!/usr/bin/env python3

import requests, json

api_headers = { "x-salechannel" : "3c4b1c81-e854-4324-830f-d59bec8cf9a2" }

keys = ["id", "title", "subtitle", "slug", "organization_id", "cycle", "featuredImage", "totalCapacity", "occupiedCapacity", "eventStart", "eventEnd", "eventDateRange", "metas", "rooms", "spaces", "validFrom", "joboMembership", "private" ]

try:
    response = requests.get("https://api2-tienda.madrid-destino.com/public_api/organizations", headers=api_headers)
    data = response.json()["data"]
except Exception as e:
    print(e)
else:
    for place in data:
        # for event in filter(lambda e: e["joboMembership"], place["events"]):
        for event in place["events"]:
            # for key in event.keys():
            for key in keys:
                print(f'{key}: {event[key]}')
            print(f'https://tienda.madrid-destino.com/es/{place["slug"]}/{event["slug"]}')
            print("\n"*3)
