import os

def compile_js(quiet=False):

    if not quiet:
        print("Compiling Javascript...")

    os.system("java -jar tools/closure-compiler.jar "
              "--language_in ECMASCRIPT5 "
              "--compilation_level ADVANCED_OPTIMIZATIONS "
              "--js app/js/healthmap.js "
              "--externs app/js/externs_d3.js "
              "--externs app/js/externs_mapbox.js "
              "--formatting=pretty_print "
              "--js_output_file app/js/bundle.js")


if __name__ == "__main__":
    compile_js()
