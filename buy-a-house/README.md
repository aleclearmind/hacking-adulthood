# Buy a house

This script can help you better restrict the houses you have to visit.

Features:

* Compute distance from set of known POIs.
* Compute distance from user-provided POIs.
* Compute price per square meter.
* Query with SQL
* Put things on a map

It currently uses immobiliare.it and provides distance from bikemi/metro stations in Milan.
It should be easy to extend.

## Collecting useful data

Create a `houses.csv` similar to the following:

```
url,vote
https://www.immobiliare.it/annunci/.../,9
```

And run:

```sh
pip3 install --user geopy
./collect-info.py houses.csv houses.db --poi duomo,45.464167,9.191389
```

You can now query your SQLite DB:

```sh
sqlite3 houses.db <<eof
.headers on
.mode table
SELECT * FROM results;
eof
```

## Putting things on a map

You can create a GPX file:

```sh
./db-to-gpx.py houses.db > houses.gpx
```

To open it, you can use [QGIS](https://qgis.org/) or [Viking](https://sourceforge.net/projects/viking/).
