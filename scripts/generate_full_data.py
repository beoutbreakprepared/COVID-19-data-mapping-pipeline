#!/usr/bin/env python3
"""
Pull data from latestdata.csv, and JHU repo for US
split into daily slices.
"""

import argparse
import json
import multiprocessing
import os
import re
import sys

from io import StringIO

import pandas as pd
import requests

import functions
import split

JHU_URL = "https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_US.csv"

LATEST_DATA_URL = "https://raw.githubusercontent.com/beoutbreakprepared/nCoV2019/master/latest_data/latestdata.tar.gz"


parser = argparse.ArgumentParser(description="Generate data for the frontend")

parser.add_argument("out_dir", type=str, default=".", help="path to dailies directory")

parser.add_argument("-l", "--latest", type=str, default=False,
    help="path to read latestdata.csv locally, fetch from github otherwise"
)

parser.add_argument("-f", "--full", type=str, default=False,
    help="option to save full-data"
)

parser.add_argument("-j", "--jhu", type=str, default=False,
    help="Option to save jhu data (before formating)"
)

parser.add_argument("-t", "--timeit", action="store_const", const=True,
    help="option to print execution time"
)

parser.add_argument("--input_jhu", default="", type=str,
    help="read from local jhu file"
)


def generate_geo_ids(df, lat_field_name, lng_field_name, quiet=False):
    if not quiet:
        print("Rounding latitudes and longitudes...")
    df[lat_field_name] = df[lat_field_name].apply(functions.round_lat_long)
    df[lng_field_name] = df[lng_field_name].apply(functions.round_lat_long)

    if not quiet:
        print("Generating 'geo ids'...")
    df["geoid"] = df[lat_field_name] + "|" + df[lng_field_name]

    return df


def prepare_latest_data(countries, quiet=False):
    if not quiet:
        print("Downloading latest data...")
    os.system("curl --silent '" + LATEST_DATA_URL + "' > latestdata.tgz")
    os.system("tar xzf latestdata.tgz")
    os.remove("latestdata.tgz")

    try:
        if not quiet:
            print("Reading the latest data...")
        df = pd.read_csv(
            "latestdata.csv",
            usecols=[
                "city",
                "province",
                "country",
                "date_confirmation",
                "latitude",
                "longitude",
            ],
        )
        os.remove("latestdata.csv")

    except ValueError:
        print(
            "I couldn't read data from the source file. Is there something "
            "wrong with the data at '" + LATEST_DATA_URL + "'?"
        )
        sys.exit(1)

    df["latitude"] = df.latitude.astype(str)
    df["longitude"] = df.longitude.astype(str)

    if not quiet:
        print("Applying filters...")
    df = df[~df.country.isin(["United States", "Virgin Islands, U.S.", "Puerto Rico"])]
    df = df[~df.latitude.isnull() | df.longitude.isnull()]
    df = df[~df.latitude.str.contains("[aA-zZ]", regex=True)]
    df = df[~df.longitude.str.contains("[aA-zZ]", regex=True)]
    df["date_confirmation"] = df.date_confirmation.str.extract("(\d{2}\.\d{2}\.\d{4})")
    df = df[
        pd.to_datetime(df.date_confirmation, format="%d.%m.%Y", errors="coerce")
        < pd.datetime.now()
    ]

    generate_geo_ids(df, "latitude", "longitude", quiet=quiet)

    # Extract mappings between lat|long and geographical names, then only keep
    # the geo_id.
    if not quiet:
        print("Extracting location info...")
    functions.compile_location_info(df.to_dict("records"),
        "app/location_info_world.data", countries, quiet=quiet)
    df = df.drop(["city", "province", "country", "latitude", "longitude"], axis=1)

    dates = df.date_confirmation.unique()
    geoids = df.geoid.unique()
    geoids.sort()

    new = pd.DataFrame(columns=geoids, index=dates)
    new.index.name = "date"
    for i in new.index:
        counts = df[df.date_confirmation == i].geoid.value_counts()
        new.loc[i] = counts
    new = new.fillna(0)
    new.reset_index(drop=False)
    return new


def prepare_jhu_data(outfile, read_from_file, countries, quiet=False):
    """Gets JHU US data from the URL and formats it for the client."""

    if read_from_file:
        read_from = read_from_file
    else:
        # Get JHU data
        if not quiet:
            print("Downloading data from JHU...")
        req = requests.get(JHU_URL)
        if req.status_code != 200:
            print("Could not get JHU data, aborting")
            sys.exit(1)
        read_from = StringIO(req.text)

    df = pd.read_csv(read_from)

    if outfile:
        df.to_csv(outfile, index=False)

    roundto = functions.LAT_LNG_DECIMAL_PLACES
    df["Lat"] = df.Lat.round(roundto)
    df["Long_"] = df.Long_.round(roundto)

    # do some filtering
    df = df.dropna()
    df = df[df.Admin2 != "Unassigned"]
    df = df[~((df.Lat == 0) & (df.Long_ == 0))]

    generate_geo_ids(df, "Lat", "Long_", quiet=quiet)

    functions.compile_location_info(df.to_dict("records"),
        "app/location_info_us.data", countries,
        keys=["Country_Region", "Province_State", "Admin2"],
        quiet=quiet)

    rx = "\d{1,2}/\d{1,2}/\d"
    date_columns = [c for c in df.columns if re.match(rx, c)]
    keep = ["geoid"] + date_columns
    df = df[keep]

    # rename to match latestdata format
    new_dates = []
    for c in date_columns:
        month, day, year = c.split("/")
        month = month.zfill(2)
        day = day.zfill(2)
        year = "20" + year if len(year) == 2 else year
        new = f"{day}.{month}.{year}"
        new_dates.append(new)
    df.rename(dict(zip(date_columns, new_dates)), axis=1, inplace=True)

    df = df.set_index("geoid")
    df = df - df.shift(1, axis=1).fillna(0).astype(int)

    # some entries are inconsistent, i.e. not really cumulative for those
    # we assign a value of zero (for new cases).  Induces a bit of error, but
    # preferable than ignoring entirely.
    df[df < 0] = 0

    df = df.T
    df.index.name = "date"
    df.reset_index(inplace=True)
    return df


def generate_data(out_dir, jhu=False, input_jhu="", export_full_data=False,
                  overwrite=False, quiet=False):

    countries = functions.read_country_data(quiet=quiet)
    latest = prepare_latest_data(countries, quiet=quiet)
    jhu = prepare_jhu_data(jhu, input_jhu, countries, quiet=quiet)

    full = latest.merge(jhu, on="date", how="outer")
    full.fillna(0, inplace=True)
    full = full.set_index("date")
    for c in full.columns:
        if c == "date":
            continue

        full[c] = full[c].astype(int)

    # drop columns with negative values (errors in JHU data)
    # Hopefully they will be fixed at some point.
    if export_full_data:
        full.to_csv(export_full_data)

    full.index = [split.normalize_date(x) for x in full.index]
    full.index.name = "date"
    full = full.sort_values(by="date")

    new_cases = full
    total_cases = new_cases.cumsum()

    n_cpus = multiprocessing.cpu_count()
    if not quiet:
        print("Processing " + str(len(full)) + " features "
              "with " + str(n_cpus) + " threads...")

    pool = multiprocessing.Pool(n_cpus)
    out_slices = pool.starmap(split.daily_slice,
                              split.chunks(new_cases, total_cases),
                              chunksize=10)

    index = []
    for s in out_slices:
        out_name = s["date"].replace("-", ".") + ".json"
        daily_slice_file_path = os.path.join(out_dir, out_name)
        index.append(out_name)

        if not overwrite and os.path.exists(daily_slice_file_path):
            print(
                "I will not clobber '" + daily_slice_file_path + "', "
                "please delete it first"
            )
            continue

        with open(daily_slice_file_path, "w") as f:
            f.write(json.dumps(s))

        with open(os.path.join(out_dir, "index.txt"), "w") as f:
            # Reverse-sort the index file so that the browser will fetch recent
            # slices first.
            f.write("\n".join(sorted(index, reverse=True)))
            f.close()

    # Concatenate location info for the US and elsewhere
    os.system("rm -f app/location_info.data")
    os.system("cat app/location_info_world.data app/location_info_us.data > "
              "app/location_info.data")
    os.remove("app/location_info_world.data")
    os.remove("app/location_info_us.data")


if __name__ == "__main__":
    args = parser.parse_args()

    if args.timeit:
        import time
        t0 = time.time()

    generate_data(args.out_dir, args.jhu, args.input_jhu, args.full)

    if args.timeit:
        print(round(time.time() - t0, 2), "seconds")
