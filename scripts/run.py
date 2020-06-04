import data_util
import os
import shlex
import subprocess
import sys
import threading


def run_sass_precompiler():
    input_files = [f for f in os.listdir("css") if f.endswith(".scss")]
    if not len(input_files):
        return None
    return subprocess.call(shlex.split("sass --watch css:css"))


def run_http_server():
    # Uses port 8000 by default.
    return subprocess.call(shlex.split("python3 -m http.server"))


def run():
    data_util.make_country_pages()

    try:
        os.chdir("app")
        http = threading.Thread(target=run_http_server)
        sass = threading.Thread(target=run_sass_precompiler)
        http.start()
        sass.start()
        http.join()
        sass.join()

    except KeyboardInterrupt:
        print("Shutting down...")
        sys.exit(0)
