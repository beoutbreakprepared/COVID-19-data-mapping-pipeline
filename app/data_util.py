import glob
import os
import sys

sys.path.append("../scripts")
import split

# The file containing all the data we need, and where to get it.
FULL_DATA_FILE = "full-data.json"
FULL_DATA_FILE_URL = "https://www.dl.dropboxusercontent.com/s/t48xylj81vaw25g/full-data.json"

# The directory where JSON files for daily data are expected to be.
DAILIES_DIR = "dailies"  

LOCATION_INFO_PATH = "location_info.data"

# A map from the data file we expect to where we can fetch it.                           
DATA_FILES = {
  "who.json": "https://www.healthmap.org/covid-19/who.json",
  FULL_DATA_FILE: FULL_DATA_FILE_URL,
}

# Returns whether we were able to get the necessary data
def retrieve_generable_data(out_dir, should_overwrite=False):
  import get_WHO_data
  import scrape_total_count

  success = True
  out_path = os.path.join(out_dir, "who.json")
  if not os.path.exists(out_path) or should_overwrite:
    success &= get_WHO_data.get_WHO(out_path)
  out_path = os.path.join(out_dir, "latestCounts.json")
  if not os.path.exists(out_path) or should_overwrite:
    success &= scrape_total_count.scrape_total_count(out_path)

  return success

def prepare_for_local_development():
  if not os.path.exists(DAILIES_DIR):
    os.mkdir(DAILIES_DIR)

  # Download the data we don't yet have.
  for f in DATA_FILES:
    if not os.path.exists(f):
      print("We don't have '" + f + "', downloading it...")
      os.system("curl '" + DATA_FILES[f] + "' > " + f)

  if not os.path.exists(LOCATION_INFO_PATH):
    print("Generating location info data...")
    split.compile_location_info(FULL_DATA_FILE, LOCATION_INFO_PATH)

  dailies = os.listdir(DAILIES_DIR)
  if len(dailies) > 0:
    print("I found some daily data ready to use. To re-generate, empty "
          "the '" + DAILIES_DIR + "' directory (or run './clean') and start me "
          "again.")
  else:
    generate_daily_slices(FULL_DATA_FILE)
  return False

def prepare_for_deployment():
  self_dir = os.path.dirname(os.path.realpath(__file__))
  os.chdir(self_dir)
  # For deployment, we check the presence of the data we need, but we don't
  # automatically download it.
  have_all = True
  for f in DATA_FILES:
    if not os.path.exists(f):
      print("Please get the latest '" + f + "' file and place "
            "it in '" + self_dir + "', then call me again.")
      print("If you don't have the latest version, try this "
            "link: '" + DATA_FILES[f] + "'")
      have_all = False
  if not have_all:
    sys.exit(1)
  if not os.path.exists(DAILIES_DIR):
    os.mkdir(DAILIES_DIR)
  # Clean whatever is left over.
  for daily in glob.glob("dailies/*.json"):
    os.remove(daily)
  if os.path.exists(LOCATION_INFO_PATH):
    os.remove(LOCATION_INFO_PATH)
  print("Generating location info data...")
  split.compile_location_info(FULL_DATA_FILE, LOCATION_INFO_PATH)

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
