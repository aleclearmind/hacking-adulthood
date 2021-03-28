#!/usr/bin/env python3

import argparse
import json
import os
import sqlite3
import sys

def main():
    parser = argparse.ArgumentParser(description='.')
    parser.add_argument('db', metavar='DB', help='input DB.')
    parser.add_argument('sql',
                        metavar='SQL',
                        nargs="?",
                        default="SELECT * FROM results",
                        help='SQL query.')
    args = parser.parse_args()

    db = sqlite3.connect(args.db)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()

    print("""<?xml version="1.0" encoding="UTF-8"?>
<gpx
  version="1.1"
  creator="Runkeeper - http://www.runkeeper.com"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns="http://www.topografix.com/GPX/1/1"
  xsi:schemaLocation="http://www.topografix.com/GPX/1/1 http://www.topografix.com/GPX/1/1/gpx.xsd"
  xmlns:gpxtpx="http://www.garmin.com/xmlschemas/TrackPointExtension/v1">""")

    for index, row in enumerate(cursor.execute(args.sql)):
        print(f"""
        <wpt lat="{row["latitude"]}" lon="{row["longitude"]}">
          <name>{index}</name>
          <desc>{json.dumps(dict(row), indent=2)}</desc>
        </wpt>
        """)

    print("""</gpx>""")

if __name__ == "__main__":
    sys.exit(main())
