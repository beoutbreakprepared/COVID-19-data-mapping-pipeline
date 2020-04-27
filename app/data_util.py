import glob
import os
import sys

sys.path.append("../scripts")
import split

# The file containing all the data we need, and where to get it.
FULL_DATA_FILE = "full-data.json"
FULL_DATA_TAR  = FULL_DATA_FILE.replace('.json', '.tar.gz')
FULL_DATA_FILE_URL = 'https://dl.dropboxusercontent.com/s/33mixinoi076x9f/full-data.tar.gz?dl=0'

# The directory where JSON files for daily data are expected to be.
DAILIES_DIR = "dailies"

COUNTRY_DATA_PATH = "countries.data"
LOCATION_INFO_PATH = "location_info.data"

self_dir = os.path.dirname(os.path.realpath(__file__))

# Returns whether we were able to get the necessary data
def retrieve_generable_data(out_dir, should_overwrite=False):
  import scrape_total_count

  success = True
  out_path = os.path.join(out_dir, "latestCounts.json")
  if not os.path.exists(out_path) or should_overwrite:
    success &= scrape_total_count.scrape_total_count(out_path)

  return success

def prepare_for_local_development():
  if not os.path.exists(DAILIES_DIR):
    os.mkdir(DAILIES_DIR)

  # Download the data if we don't yet have it.
  if not os.path.exists(FULL_DATA_FILE):
    print("We don't have '" + FULL_DATA_FILE + "', downloading it...")
    os.system("curl '" + FULL_DATA_FILE_URL + "' > " + FULL_DATA_TAR)
    os.system("tar -xzf " + FULL_DATA_TAR)


  retrieve_generable_data(self_dir, should_overwrite=False)

  if not os.path.exists(LOCATION_INFO_PATH):
    print("Generating location info data...")
    split.compile_location_info(
        FULL_DATA_FILE, LOCATION_INFO_PATH, COUNTRY_DATA_PATH)

  dailies = os.listdir(DAILIES_DIR)
  if len(dailies) > 0:
    print("I found some daily data ready to use. To re-generate, empty "
          "the '" + DAILIES_DIR + "' directory (or run './clean') and start me "
          "again.")
  else:
    generate_daily_slices(FULL_DATA_FILE)
  return False

def prepare_for_deployment():
  os.chdir(self_dir)
  # For deployment, we check the presence of the "full data", but we don't
  # automatically download it.
  if not os.path.exists(FULL_DATA_FILE):
    print("Please get the latest '" + FULL_DATA_FILE + "' file and place "
          "it in '" + self_dir + "', then call me again.")
    print("If you don't have the latest version, try this "
          "link: '" + FULL_DATA_FILE_URL + "'")
    sys.exit(1)

  if not retrieve_generable_data(self_dir, should_overwrite=True):
    print("I wasn't able to retrieve necessary data, aborting")
    sys.exit(1)

  if not os.path.exists(DAILIES_DIR):
    os.mkdir(DAILIES_DIR)
  # Clean whatever is left over.
  for daily in glob.glob("dailies/*.json"):
    os.remove(daily)
  if os.path.exists(LOCATION_INFO_PATH):
    os.remove(LOCATION_INFO_PATH)
  print("Generating location info data...")
  split.compile_location_info(
    FULL_DATA_FILE, LOCATION_INFO_PATH, COUNTRY_DATA_PATH)

  generate_daily_slices(FULL_DATA_FILE)

def split_data(FULL_DATA_FILE, out_dir):
  if sys.version_info[0] < 3:
    print("Sorry, but I need Python 3 to work")
    sys.exit(1)
  split.split_full_data_to_daily_slices(FULL_DATA_FILE, DAILIES_DIR)

def generate_daily_slices(full_data_file_path):
  print("I need to generate the daily slices, this is going to take "
        "a few minutes...")
  split_data(FULL_DATA_FILE, DAILIES_DIR)
