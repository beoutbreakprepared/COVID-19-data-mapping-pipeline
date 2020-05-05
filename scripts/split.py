import json
import functions
import os
import sys

TEMP_JSON = "temp.json"
TOPLEVEL_KEY = "data"

# Geo properties that the client doesn't use and that we can prune out.
PROPERTIES_TO_PRUNE = [
    "date",
    "geo_resolution",
]

def normalize_date(date):
    date = date.replace("-", ".")
    if len(date) == len("D.MM.YYYY"):
        # Single day digit
        date = date.zfill(len("DD.MM.YYYY"))
    # Reverse DD.MM.YYYY into YYYY.MM.DD so that alphabetical order is the
    # same as chronological.
    date_parts = date.split(".")
    if len(date_parts[0]) != 4:
        date_parts.reverse()
    return ".".join(date_parts)

def convert_to_client_format(file_path):
    functions.animation_formating_geo(file_path, TEMP_JSON)
