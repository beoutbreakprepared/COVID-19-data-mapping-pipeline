"""
Makes it easy and painless to deploy the site and make all necessary changes
so that it's immediately ready to serve in production.
"""
import datetime
import os
import shlex
import subprocess
import sys

import data_util
import js_compilation

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
    "js/healthmap.js",
    "prerequisites.md",
    "run",
]

BACKUP_DIR_PREFIX = "backup_"

# Returns True if everything we need is here, False otherwise.
def check_dependencies():
    try:
        subprocess.check_call(shlex.split("sass --version"), stdout=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        print("Please install 'sass' first.")
        return False
    return True


def has_analytics_code():
    return os.system("grep --quiet 'google-analytics.com' app/index.html") == 0


def insert_analytics_code(quiet=False):
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

    # Remove the file and write a modified version
    os.system("rm app/index.html")
    with open("app/index.html", "w") as f:
        f.write(main_page)
        f.close()


def use_compiled_js():
    js_compilation.compile_js()

    # Now link to the compiled code in the HTML file
    main_page = ""
    scripting_time = False
    with open("app/index.html") as f:
        for line in f:
            if line.strip() == "<!-- /js -->":
                scripting_time = False
                main_page += '<script src="js/bundle.js"></script>\n'
            elif scripting_time:
                continue
            elif line.strip() == "<!-- js -->":
                scripting_time = True
            else:
                main_page += line
        f.close()

    # Remove the file and write a modified version
    os.system("rm app/index.html")
    with open("app/index.html", "w") as f:
        f.write(main_page)
        f.close()


def backup_pristine_files():
    os.system("cp app/index.html app/index.html.orig")


def restore_pristine_files():
    os.system("mv app/index.html.orig app/index.html")


# Returns whether the backup operation succeeded
def backup_current_version(target_path, quiet=False):
    timestamp = datetime.datetime.now().strftime("%Y.%m.%d_%H.%M.%S")
    backup_dir = BACKUP_DIR_PREFIX + timestamp

    if not quiet:
        print("Backing up current version into '" + backup_dir + "'...")
    return os.system("cp -a " + target_path + " " + backup_dir) == 0


def copy_contents(target_path, quiet=False):
    if not quiet:
        print("Replacing target contents with new version...")
    # TODO: Use 'rsync' if it's available.
    os.system("rm -rf " + target_path + "/*")
    to_copy = [
        "'app/" + f + "'"
        for f in os.listdir("app")
        if f not in EXCLUDED
        and not f.startswith(BACKUP_DIR_PREFIX)
        and not f.endswith(".orig")
    ]
    cmd = "cp -a " + " ".join(to_copy) + " " + target_path + "/"
    os.system(cmd)


def deploy(target_path, quiet=False):
    if not check_dependencies():
        sys.exit(1)
    backup_pristine_files()
    data_util.prepare_for_deployment(quiet=quiet)
    os.system("sass app/css/styles.scss app/css/styles.css")

    if has_analytics_code():
        if not quiet:
            print("Analytics code is already present, skipping that step.")
    else:
        insert_analytics_code(quiet=quiet)
    use_compiled_js()

    if not backup_current_version(target_path, quiet=quiet):
        print("I could not back up the current version, bailing out.")
        sys.exit(1)

    copy_contents(target_path, quiet=quiet)
    restore_pristine_files()

    if not quiet:
        print("All done. You can test it out with: "
              "cd " + target_path + " && python3 -m http.server")
