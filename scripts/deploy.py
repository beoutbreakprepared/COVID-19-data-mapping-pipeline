import datetime
import os
import shlex
import subprocess
import sys

import data_util

# Files and directories inside "app" that do not need to be copied over
# to the target. Please keep alphabetized.
EXCLUDED = [
    "__pycache__",
    "analytics.js",
    "clean",
    "data_util.py",
    "deploy",
    "full-data.json",
    "full-data.tar.gz",
    "prerequisites.md",
    "run",
]

BACKUP_DIR_PREFIX = "backup_"

# Returns True if everything we need is here, False otherwise.
def check_dependencies():
    try:
        subprocess.check_call(shlex.split("sass --version"))
    except (subprocess.CalledProcessError, OSError):
        print("Please install 'sass' first.")
        return False
    return True

def has_analytics_code():
    return os.system("grep 'google-analytics.com' app/index.html") == 0

def insert_analytics_code():
    main_page = ""
    with open("app/analytics.js") as f:
        code = f.read()
        f.close()
    inserted = False
    with open("app/index.html") as f:
        for line in f:
            if not inserted and "<script" in line:
                main_page += code
                inserted = True
        main_page += line
        f.close()

    # Back-up the file write a modified version
    os.system("mv app/index.html app/index.html.orig")
    with open("app/index.html", "w") as f:
        f.write(main_page)
        f.close()

def restore_pristine_files():
    os.system("mv app/index.html.orig app/index.html")

# Returns whether the backup operation succeeded
def backup_current_version(target_path):
    timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    backup_dir = BACKUP_DIR_PREFIX + timestamp
    print("Backing up current version into '" + backup_dir + "'...")
    return os.system("cp -a " + target_path + " " + backup_dir) == 0

def copy_contents(target_path):
    print("Replacing target contents with new version...")
    # TODO: Use 'rsync' if it's available.
    os.system("rm -rf " + target_path + "/*")
    to_copy = ["'app/" + f + "'" for f in os.listdir("app")
               if f not in EXCLUDED
               and not f.startswith(BACKUP_DIR_PREFIX)
               and not f.endswith(".orig")]
    cmd = "cp -a " + " ".join(to_copy) + " " + target_path + "/"
    os.system(cmd)

def deploy(target_path):
    if not check_dependencies():
        sys.exit(1)
    data_util.prepare_for_deployment()
    os.system("sass app/css/styles.scss app/css/styles.css")

    if has_analytics_code():
        print("Analytics code is already present, skipping that step.")
    else:
        insert_analytics_code()

    if not backup_current_version(target_path):
        print("I could not back up the current version, bailing out.")
        sys.exit(1)

    copy_contents(target_path)
    restore_pristine_files()

    print("All done.")
