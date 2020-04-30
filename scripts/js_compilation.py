import os

os.chdir("app/js")

os.system("closure-compiler "
          "--language_in ECMASCRIPT5 "
          "--js healthmap.js "
          "--js_output_file bundle.js")
