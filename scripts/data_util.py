import glob
import os
import pandas
import sys

sys.path.append("scripts")
import generate_full_data
import jhu_global_data

# The directory where JSON files for country-specific and day-specific data
# are expected to reside.
COUNTRIES_DIR = "app/countries"
DAILIES_DIR = "app/dailies"

self_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

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

# Returns whether we were able to get the necessary data
def retrieve_generable_data(out_dir, should_overwrite=False, quiet=False):
    import scrape_total_count

    success = True
    out_path = os.path.join(out_dir, "latestCounts.json")
    if not os.path.exists(out_path) or should_overwrite:
        success &= scrape_total_count.scrape_total_count(out_path)
    out_path = os.path.join(out_dir, "jhu.json")
    if not os.path.exists(out_path) or should_overwrite:
        success &= jhu_global_data.main(out_path)

    return success


def prepare_for_local_development(quiet=False):
    if not os.path.exists(COUNTRIES_DIR):
        os.mkdir(COUNTRIES_DIR)
    if not os.path.exists(DAILIES_DIR):
        os.mkdir(DAILIES_DIR)

    countries = [f for f in os.listdir(COUNTRIES_DIR) if f.endswith(".json")]
    dailies = [f for f in os.listdir(DAILIES_DIR) if f.endswith(".json")]
    if len(countries) > 0 and len(dailies) > 0:
        if not quiet:
            print(
                "I found some daily data ready to use. To re-generate, "
                "empty the '" + DAILIES_DIR + "' directory (or "
                "run './clean') and start me again."
            )
    else:
        generate_data(quiet=quiet)

    retrieve_generable_data(
        os.path.join(self_dir, "app"), should_overwrite=False, quiet=quiet
    )

    return False


def prepare_for_deployment(quiet=False):
    os.chdir(self_dir)

    if not retrieve_generable_data(
        os.path.join(self_dir, "app"), should_overwrite=True, quiet=quiet
    ):
        print("I wasn't able to retrieve necessary data, aborting")
        sys.exit(1)

    if not os.path.exists(DAILIES_DIR):
        os.mkdir(DAILIES_DIR)
    if not os.path.exists(COUNTRIES_DIR):
        os.mkdir(COUNTRIES_DIR)

    # Clean whatever is left over.
    for daily in glob.glob("dailies/*.json"):
        os.remove(daily)
    for country in glob.glob("countries/*.json"):
        os.remove(country)

    generate_data(overwrite=True, quiet=quiet)


def generate_data(overwrite=False, quiet=False):
    if not quiet:
        print(
            "I need to generate the appropriate data, this is going to "
            "take a few minutes..."
        )
    generate_full_data.generate_data(
        os.path.join(self_dir, DAILIES_DIR),
        os.path.join(self_dir, COUNTRIES_DIR),
        overwrite=overwrite, quiet=quiet
    )
