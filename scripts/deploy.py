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
    ".gitignore",
    ".sass-cache",
    "analytics.js",
    "css/styles.scss",
    "css/styles.css.map",
    "js/externs_d3.js",
    "js/externs_mapbox.js",
    "js/healthmap.js",
    "js/healthmap_test.js",
]

BACKUP_DIR_PREFIX = "backup_"

# Returns True if everything we need is here, False otherwise.
def check_dependencies():
    try:
        subprocess.check_call(shlex.split("sass --version"),
                              stdout=subprocess.DEVNULL)
    except (subprocess.CalledProcessError, OSError):
        print("Please install 'sass' first.")
        return False
    # If the Closure compiler isn't available, let's get that setup.
    if not os.path.exists("tools/closure-compiler.jar"):
        print("The Closure compiler isn't available, fetching it. "
              "This will only happen once.")
        os.system("curl \"https://dl.google.com/closure-compiler/"
                  "compiler-latest.zip\" > compiler-latest.zip")
        if not os.path.exists("tools"):
            os.mkdir("tools")
        os.system("unzip -d tools compiler-latest.zip")
        os.system("mv tools/closure-compiler*.jar tools/closure-compiler.jar")
        os.system("rm -rf tools/COPYING tools/README.md")
        os.system("rm -f compiler-latest.zip")

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


def link_to_compiled_js_in_html(html_file):
    # Now link to the compiled code in the HTML file
    html = ""
    scripting_time = False
    with open(html_file) as f:
        for line in f:
            if line.strip() == "<!-- /js -->":
                scripting_time = False
                html += '<script src="/js/bundle.js"></script>\n'
            elif scripting_time:
                continue
            elif line.strip() == "<!-- js -->":
                scripting_time = True
            else:
                html += line
        f.close()

    # Remove the file and write a modified version
    os.system("rm " + html_file)
    with open(html_file, "w") as f:
        f.write(html)
        f.close()


def use_compiled_js(quiet=False):
    js_compilation.compile_js(quiet)
    link_to_compiled_js_in_html("app/index.html")
    link_to_compiled_js_in_html("app/country.html")


def backup_pristine_files():
    os.system("cp app/index.html app/index.html.orig")
    os.system("cp app/country.html app/country.html.orig")


def restore_pristine_files():
    os.system("mv app/index.html.orig app/index.html")
    os.system("mv app/country.html.orig app/country.html")


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

    use_compiled_js(quiet=quiet)

    data_util.prepare_for_deployment(quiet=quiet)
    os.system("sass app/css/styles.scss app/css/styles.css")

    if has_analytics_code():
        if not quiet:
            print("Analytics code is already present, skipping that step.")
    else:
        insert_analytics_code(quiet=quiet)

    if not backup_current_version(target_path, quiet=quiet):
        print("I could not back up the current version, bailing out.")
        sys.exit(1)

    copy_contents(target_path, quiet=quiet)
    restore_pristine_files()

    if not quiet:
        print("All done. You can test it out with: "
              "cd " + target_path + " && python3 -m http.server")
