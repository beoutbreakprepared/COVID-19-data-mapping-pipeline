"""Some utilities to split data according to time or location."""
import multiprocessing

def normalize_date(date):
    """Returns an ISO string representation of a date string."""
    date = date.replace(".", "-")
    if len(date) == len("D-MM-YYYY"):
        # Single day digit
        date = date.zfill(len("DD-MM-YYYY"))
    # Reverse DD-MM-YYYY into YYYY-MM-DD so that alphabetical order is the
    # same as chronological.
    date_parts = date.split("-")
    if len(date_parts[0]) != 4:
        date_parts.reverse()
    return "-".join(date_parts)

def slice_by_day(full, quiet=False):
    full.index = [normalize_date(x) for x in full.index]
    full.index.name = "date"
    full = full.sort_values(by="date")

    new_cases = full
    total_cases = new_cases.cumsum()

    n_cpus = multiprocessing.cpu_count()
    if not quiet:
        print("Processing " + str(len(full)) + " features "
              "with " + str(n_cpus) + " threads...")

    pool = multiprocessing.Pool(n_cpus)
    return pool.starmap(daily_slice,
                        chunks(new_cases, total_cases, quiet),
                        chunksize=10)

def daily_slice(new_cases, total_cases):
    # full starts from new cases by location/date
    # structure for daily slice YYYY-MM-DD.json
    # {"date": "YYYY-MM-DD", "features": [{"properties": {"geoid": "lat|long",
    # "new": int, "total": int}}, ... ]

    assert new_cases.name == total_cases.name, "mismatched dates"

    features = []

    for geoid in new_cases.index:
        new = int(new_cases[geoid])
        total = int(total_cases[geoid])
        if new == total == 0:
            continue
        properties = {"geoid": geoid, "total": total}
        if new != 0:
            properties["new"] = new

        features.append({"properties": properties})

    return {"date": new_cases.name, "features": features}


def write_single_country_data(iso_code, data_frame):
    features = []
    data_frame = data_frame.rename(columns={"date_confirmation": "date"})
    data_frame = data_frame.sort_values("date")

def slice_by_country(data_frame, countries, quiet=False):
    groups = data_frame.groupby("country")
    for g in groups:
        (country, frame) = g
        if country not in countries:
            print("Warning: I don't know about '" + country + "'")
            continue
        country_iso = countries[country]
        write_single_country_data(country_iso, frame)

def chunks(new_cases, total_cases, quiet=False):
    """
    Yields successive equal-sized chunks from the input list.
    """
    for i in range(len(new_cases)):
        if not quiet:
            print(".", end="", flush=True)
        yield (new_cases.iloc[i], total_cases.iloc[i])
