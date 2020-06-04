import base_test
import os
import sys

sys.path.append("scripts")
from deploy import deploy

TEST_TARGET = "test_deployment"

class DeployTest(base_test.BaseTest):

    def display_name(self):
        return "Deployment tests"

    def target_file_contains(self, path, pattern):
        return os.system("grep --quiet '" + pattern + "' " + \
             os.path.join(TEST_TARGET, path)) == 0

    def target_file_exists(self, path):
        return os.path.exists(os.path.join(TEST_TARGET, path))

    def run(self):
        if os.path.exists(TEST_TARGET):
            # Previous run may have failed.
            os.system("rm -rf " + TEST_TARGET)
        os.mkdir(TEST_TARGET)
        # Note: set 'quiet' to True for debugging failures.
        deploy(os.path.join(os.getcwd(), TEST_TARGET), quiet=True)

        self.check(
            self.target_file_contains("index.html", "google-analytics"),
            "The deployed index file should contain analytics code")

        self.check(
            self.target_file_contains("index.html", "<body>"),
            "The deployed index file should contain the basic HTML")

        self.check(
            self.target_file_contains("index.html", "fetchAboutPage"),
            "The index page needs to make an unobfuscated call "
            "to 'fetchAboutPage'")

        self.check(self.target_file_exists("js/bundle.js"),
                   "Javascript should get compiled as part of deployment.")
        self.check(not self.target_file_exists("js/healthmap.js"),
                   "Original Javascript files shouldn't be copied to "
                   "the target.")

    def tear_down(self):
        if self.passed():
            # Clean up if everything went well.
            os.system("rm -rf " + TEST_TARGET)
        else:
            print("I will leave the test deployment in "
                  "'" + TEST_TARGET + "' for inspection")
        super().tear_down()
