import base_test
import os
import re

SRC_FILES = [
    "app/js/healthmap.js",
]

TEST_FILES = [
    "tests/base_test.js",
    "app/js/healthmap_test.js",
]

TEMP_TEST_CONCATENATION = "js_test_temp.js"

TEST_METHOD_REGEXP = r"function\s+(test.+)\("

class JsTest(base_test.BaseTest):
    def display_name(self):
        return "Javascript tests"

    def find_test_functions(self, contents):
        functions = []
        for line in contents.split("\n"):
            match = re.search(TEST_METHOD_REGEXP, line)
            if match:
                functions.append(match.group(1))
        return functions

    def run(self):
        test_functions = []
        full_contents = ""

        # Read the code under test.
        for s in SRC_FILES:
            with open(s) as f:
                full_contents += f.read()

        # Read the tests themselves, gathering test names.
        for t in TEST_FILES:
            with open(t) as f:
                contents = f.read()
                test_functions += self.find_test_functions(contents)
                full_contents += contents

        # Call the actual test functions.
        print("")
        for func in test_functions:
            full_contents += "console.log('\t" + func + "...');\n" + func + "();\n"
        # print("Found " + str(test_functions))
        os.system("rm -f " + TEMP_TEST_CONCATENATION)
        with open(TEMP_TEST_CONCATENATION, "w") as f:
            f.write(full_contents)
            f.close()
        return_code = os.system("nodejs " + TEMP_TEST_CONCATENATION)
        if return_code == 0:
            os.system("rm -f " + TEMP_TEST_CONCATENATION)
        self.check(return_code == 0, "JS tests failed")
