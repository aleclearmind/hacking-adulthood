#!/usr/bin/env python3

import argparse
import json
import os
import sqlite3
import sys

from csv import DictReader
from geopy.distance import geodesic
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import urlopen

def log(message):
    sys.stderr.write(message + "\n")

def url_to_name(url):
    return url.replace("/", "_").replace(":", "_").replace(".", "_")

def has_field(obj, field, url, index):
    if not field in obj or obj[field] is None:
        log(f"No {field} in property {index} of {url}")
        return False
    return True

def main():
    parser = argparse.ArgumentParser(description='.')
    parser.add_argument('csv', metavar='CSV', help='input CSV.')
    parser.add_argument('db', metavar='DB', help='output DB.')
    parser.add_argument('--poi',
                        metavar="NAME,LATITUDE,LONGITUDE",
                        action="append",
                        help='.')
    args = parser.parse_args()

    if os.path.exists(args.db):
        os.unlink(args.db)
    db = sqlite3.connect(args.db)
    cursor = db.cursor()

    pois = {}
    for poi in args.poi or []:
        name, latitude, longitude = poi.split(",")
        pois[name] = (float(latitude), float(longitude))

    for name, location in pois.items():
        for other_name, other_location in pois.items():
            if name != other_name:
                distance = geodesic(location, other_location).meters
                log(f"{name} is {distance} meters away from {other_name}")

    output_path = Path("output")
    output_path.mkdir(exist_ok=True)

    script_path = Path(os.path.dirname(os.path.realpath(__file__)))

    #
    # POIs sets
    #
    pois_sets = {}

    # Load bikemi data
    with (script_path / "bikemi.json").open(mode="r") as bikemi_json:
        pois_sets["bikemi"] = list(map(lambda line: (line[0], line[1]),
                                       json.load(bikemi_json)))

    # Load ATM data
    with (script_path / "atm.csv").open(mode="r") as atm_csv:
        pois_sets["atm"] = list(map(lambda line: list(map(float,
                                                          (line["LAT_Y_4326"],
                                                           line["LONG_X_4326"]))),
                                    list(DictReader(atm_csv, delimiter=";"))))

    distances = set(pois).union(set(pois_sets))
    cursor.execute("""
CREATE TABLE IF NOT EXISTS "results"(
  "url" TEXT,
  "vote" NUMERIC,
  "index" NUMERIC,
  "price" NUMERIC,
  "price_per_sqm" NUMERIC,
  "surface" NUMERIC,
  "latitude" NUMERIC,
  "longitude" NUMERIC,
""" + ",\n".join(f""""{name}" NUMERIC"""
                for name
                in sorted(distances)) + """
);
""")

    rows = []

    with open(args.csv, "r") as csv_file:
        for line in DictReader(csv_file):
            # Ensure we have the JSON
            url = line["url"]
            vote = float(line["vote"])
            json_path = output_path / (url_to_name(url) + ".json")
            if not json_path.exists() or json_path.stat().st_size == 0:
                domain = urlparse(url).netloc
                if domain == "www.immobiliare.it":
                    log(f"Fetching {url}")
                    data = json.loads(urlopen(url).read().decode("utf8").split("js-hydration")[1][2:].split("</script>")[0])
                    with json_path.open(mode="w") as json_file:
                        json.dump(data, json_file, indent=2)
                else:
                    raise Exception(f"Unexpected domain: {domain}")
            else:
                with json_path.open(mode="r") as json_file:
                    data = json.load(json_file)

            # Extract location
            assert len(data["listing"]["properties"]) >= 1

            last_location = None
            for index, property in enumerate(data["listing"]["properties"]):
                if "location" in property and not property["location"] is None:
                    last_location = property["location"]
                    last_location = tuple(map(float, (last_location["latitude"],
                                                      last_location["longitude"])))

                if (not (has_field(property, "surfaceValue", url, index)
                        and has_field(property, "price", url, index))
                    or property["price"]["price"] is None):
                    continue

                location = last_location

                # Distance from POIs
                distance = {}
                for poi_name, poi_location in pois.items():
                    distance[poi_name] = int(geodesic(poi_location, location).meters) / 1000

                # Minimum distance from POI sets
                for pois_set_name, pois_set_list in pois_sets.items():
                    minimum_distance = float("Inf")
                    for poi in pois_set_list:
                        minimum_distance = min(minimum_distance,
                                               geodesic(location, poi).meters)
                    distance[pois_set_name] = int(minimum_distance) / 1000
                
                # Surface
                if ("surfaceValue" not in property
                    or property["surfaceValue"] is None):
                    log(f"Warning: no surfaceValue for property {index} of {url}")
                    continue
                
                surface = int(property["surfaceValue"]
                              .replace(" m\u00b2", "")
                              .replace(",", "."))

                price = int(property["price"]["price"])

                price_per_sqm = int(price / surface) / 1000

                rows.append(
                    [
                        url,
                        vote,
                        index,
                        int(price / 1000),
                        price_per_sqm,
                        surface,
                        location[0],
                        location[1]
                    ] + [
                        str(x[1])
                        for x
                        in sorted(distance.items())
                    ]
                )

    if rows:
        columns = len(rows[0])
        cursor.executemany("INSERT INTO results VALUES("
                           + ",".join(["?" for _ in range(columns)])
                           + ")",
                           rows)

    db.commit()

    return 0

if __name__ == "__main__":
    sys.exit(main())
