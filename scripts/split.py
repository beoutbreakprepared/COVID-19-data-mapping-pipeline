"""Some utilities to split data according to time or location."""

import json
import os
import multiprocessing

def normalize_date(date):
    """Returns a normalized string representation of a date string."""
    original_argument = date
    date = date.replace(".", "-")
    date = date.replace("/", "-")
    parts = date.split("-")
    for part in parts:
        if len(part) not in [1, 2, 4]:
            raise TypeError("I can't make sense of this date format: "
                            "'" + original_argument + "'")
    if len(parts[0]) <= 2 and len(parts[1]) <= 2 and len(parts[2]) <= 2:
        raise TypeError("This date format is ambiguous: "
                        "'" + original_argument + "'. "
                        "Please make sure to use 4 digits for the year.")
    # Reverse DD-MM-YYYY into YYYY-MM-DD so that alphabetical order is the
    # same as chronological.
    if len(parts[0]) != 4:
        parts.reverse()
    # Zero-pad the month and day.
    parts[1] = parts[1].zfill(2)
    parts[2] = parts[2].zfill(2)
    return "-".join(parts)


def write_out(json_data, out_path, overwrite=True):
    if not overwrite and os.path.exists(out_path):
        print(
            "I will not clobber '" + out_path + "', "
            "please delete it first."
        )
        return
    with open(out_path, "w") as f:
        f.write(json.dumps(json_data))


def slice_by_day_and_export(full, out_dir, overwrite=True, quiet=False):
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
    out_slices = pool.starmap(produce_daily_slice,
                              chunks(new_cases, total_cases, quiet),
                              chunksize=10)
    index = []
    for s in out_slices:
        out_name = s["date"] + ".json"
        daily_slice_file_path = os.path.join(out_dir, out_name)
        index.append(out_name)

        write_out(s, daily_slice_file_path, overwrite)

        with open(os.path.join(out_dir, "index.txt"), "w") as f:
            # Reverse-sort the index file so that the browser will fetch recent
            # slices first.
            f.write("\n".join(sorted(index, reverse=True)))
            f.close()


def produce_daily_slice(new_cases, total_cases):
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

def write_single_country_data(iso_code, data_frame, out_dir, overwrite=True):
    features = []
    data_frame = data_frame.rename(columns={"date_confirmation": "date"})
    data_frame = data_frame.sort_values("date")
    for date in data_frame.index:
        properties = {"date": date}
        features.append({"properties": properties})

    slice_file_path = os.path.join(out_dir, iso_code + ".json")
    write_out({"features": features}, slice_file_path, overwrite)


def slice_by_country_and_export(data_frame, countries, out_dir, overwrite=True,
                                quiet=False):
    groups = data_frame.groupby("country")
    for g in groups:
        (country, frame) = g
        if country not in countries:
            print("Warning: I don't know about '" + country + "'")
            continue
        country_iso = countries[country]
        write_single_country_data(country_iso, frame, out_dir, overwrite)


def chunks(new_cases, total_cases, quiet=False):
    """
    Yields successive equal-sized chunks from the input list.
    """
    for i in range(len(new_cases)):
        if not quiet:
            print(".", end="", flush=True)
        yield (new_cases.iloc[i], total_cases.iloc[i])
