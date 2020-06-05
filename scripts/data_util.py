import glob
import os
import pandas
import sys

sys.path.append("scripts")

self_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

COUNTRIES_ISO_TO_NAME = {}
COUNTRIES_NAME_TO_ISO = {}


def initialize_country_names_and_codes():
    global COUNTRIES_ISO_TO_NAME
    global COUNTRIES_NAME_TO_ISO
    if len(COUNTRIES_ISO_TO_NAME) > 1:
        return
    COUNTRIES_ISO_TO_NAME = {}
    data_file = "countries.data"
    os.system("curl 'https://raw.githubusercontent.com/ghdsi/common/master/countries.data' > " + data_file)
    with open(data_file) as f:
        data = f.read().strip()
        f.close()
    pairs = data.split('\n')
    for p in pairs:
        (code, name, _) = p.split(":")
        COUNTRIES_ISO_TO_NAME[code] = name
        COUNTRIES_NAME_TO_ISO[name.lower()] = code
    os.remove(data_file)


def get_all_countries():
    """Returns a dictionary of country ISO codes to their name."""
    return COUNTRIES_ISO_TO_NAME
    if len(COUNTRIES_ISO_TO_NAME) > 0:
        return COUNTRIES_ISO_TO_NAME


def country_code_from_name(name):
    # Are we being passed something that's already a code?
    if len(name) == 2 and name == name.upper():
        return name
    if name.lower() in COUNTRIES_NAME_TO_ISO:
        return COUNTRIES_NAME_TO_ISO[name.lower()]
    print("WARNING: I don't know about country '" + name + "'")


def build_case_count_table_from_line_list(in_data):
    """
    This takes an input data frame where each row represents a single
    case, with a confirmation date and a geo ID, and returns a data
    frame where each row represents a single date, columns are unique
    geo IDs and cells are the sum of corresponding case counts.
    """
    unique_dates = in_data.date.unique()
    unique_geoids = in_data.geoid.unique()
    unique_geoids.sort()
    out_data = pandas.DataFrame(columns=unique_geoids, index=unique_dates)

    out_data.index.name = "date"
    for date in out_data.index:
        out_data.loc[date] = in_data[in_data.date == date].geoid.value_counts()
    out_data = out_data.fillna(0)
    out_data.reset_index(drop=False)
    return out_data


def make_country_pages():
    countries = get_all_countries()
    with open("app/country.html") as f:
        template = f.read().strip()
        f.close()
    for code in countries:
        directory = os.path.join("app", "c", code)
        if not os.path.exists(directory):
            os.makedirs(directory)
        index_file = os.path.join(directory, "index.html")
        if os.path.exists(index_file):
            os.remove(index_file)
        tokens = {
            "code": code,
            "title": countries[code],
        }
        output = template
        for t in tokens:
            output = output.replace("{{" + t + "}}", tokens[t])
        with open(index_file, "w") as i:
            i.write(output)
            i.close()
    # TODO: return False is anything bad happens.
    return True


# Fetch country names and codes at module initialization time to avoid doing it
# repeatedly.
initialize_country_names_and_codes()
