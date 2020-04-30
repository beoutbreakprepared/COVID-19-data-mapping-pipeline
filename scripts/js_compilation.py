import os

def compile_js(quiet=False):
    os.chdir("app/js")

    if not quiet:
        print("Compiling Javascript...")

    os.system("closure-compiler "
              "--language_in ECMASCRIPT5 "
              "--compilation_level ADVANCED_OPTIMIZATIONS "
              "--js healthmap.js "
              "--externs externs.js "
              "--js_output_file bundle.js")

    os.chdir("../..")


if __name__ == "__main__":
    compile_js()
