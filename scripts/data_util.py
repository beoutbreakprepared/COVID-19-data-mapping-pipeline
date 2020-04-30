import glob
import os
import sys

sys.path.append("scripts")
import generate_full_data
import split

# The directory where JSON files for daily data are expected to be.
DAILIES_DIR = "app/dailies"

self_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")

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

  dailies = os.listdir(DAILIES_DIR)
  if len(dailies) > 0:
    print("I found some daily data ready to use. To re-generate, empty "
          "the '" + DAILIES_DIR + "' directory (or run './clean') and start me "
          "again.")
  else:
    generate_data()

  retrieve_generable_data(os.path.join(self_dir, "app"), should_overwrite=False)

  return False

def prepare_for_deployment():
  os.chdir(self_dir)

  if not retrieve_generable_data(os.path.join(self_dir, "app"),
      should_overwrite=True):
    print("I wasn't able to retrieve necessary data, aborting")
    sys.exit(1)

  if not os.path.exists(DAILIES_DIR):
    os.mkdir(DAILIES_DIR)
  # Clean whatever is left over.
  for daily in glob.glob("dailies/*.json"):
    os.remove(daily)

  generate_data()

def generate_data():
  print("I need to generate the appropriate data, this is going to take "
        "a few minutes...")
  generate_full_data.generate_data(os.path.join(self_dir, DAILIES_DIR))
