import os

DEBUG = False

def compile_js(quiet=False):

    if not quiet:
        print("Compiling Javascript...")

    cmd = (
        "java -jar tools/closure-compiler.jar "
        "--language_in ECMASCRIPT6 "
        "--compilation_level ADVANCED_OPTIMIZATIONS "
        "" + ("--formatting=pretty_print " if DEBUG else "") + ""
        "--js app/js/country.js "
        "--js app/js/dataprovider.js "
        "--js app/js/timeanimation.js "
        "--js app/js/healthmap.js "
        "--externs app/js/externs_d3.js "
        "--externs app/js/externs_mapbox.js "
        "--js_output_file app/js/bundle.js"
    )
    if quiet:
        cmd += " 2> /dev/null"
    os.system(cmd)


if __name__ == "__main__":
    compile_js()
