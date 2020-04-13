import os
import sys

sys.path.append("../scripts")
import split

# The file containing all the data we need.
FULL_DATA_FILE = "full-data.json"

# The directory where JSON files for daily data are expected to be.
DAILIES_DIR = "dailies"  

# A map from the data file we expect to where we can fetch it.                           
DATA_FILES = {
  "dailies.geojson": "https://www.healthmap.org/covid-19/dailies.geojson",
  "who.json": "https://www.healthmap.org/covid-19/who.json",
  FULL_DATA_FILE: "https://www.dl.dropboxusercontent.com/s/t48xylj81vaw25g/full-data.json",
}

def prepare_for_local_development():
  if not os.path.exists(DAILIES_DIR):
    os.mkdir(DAILIES_DIR)

  # Download the data we don't yet have.
  for f in DATA_FILES:
    if not os.path.exists(f):
      print("We don't have '" + f + "', downloading it...")
      os.system("curl '" + DATA_FILES[f] + "' > " + f)

  dailies = os.listdir(DAILIES_DIR)
  if len(dailies) > 0:
    print("I found some daily data ready to use. To re-generate, empty "
          "the '" + DAILIES_DIR + "' directory (or run './clean') and start me "
          "again.")
  else:
    generate_daily_slices(FULL_DATA_FILE)
  return False

def split_data(FULL_DATA_FILE, out_dir):
  if sys.version_info[0] < 3:
    print("Sorry, but I need Python 3 to work")
    sys.exit(1)
  split.split_full_data_to_daily_slices(FULL_DATA_FILE, DAILIES_DIR)

def generate_daily_slices(full_data_file_path):
  print("I need to generate the daily slices, this is going to take "
        "a few minutes...")
  split_data(FULL_DATA_FILE, DAILIES_DIR)
