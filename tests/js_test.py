import base_test
import os

class JsTest(base_test.BaseTest):
    def display_name(self):
        return "Javascript tests"

    def run(self):
        os.system("nodejs tests/base_test.js app/js/healthmap_test.js")
