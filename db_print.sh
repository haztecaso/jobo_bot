#!/bin/sh
db=$1
if [[ -f "$db" ]]; then
    sqlite3 $db .schema
    sqlite3 -csv $db "SELECT * from events"
else
    echo $db file does not exist!
fi

