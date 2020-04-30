import base_test
import os
import sys

sys.path.append("scripts")
from deploy import deploy

TEST_TARGET = "test_deployment"

class DeployTest(base_test.BaseTest):
    def display_name(self):
        return "Deployment tests"

    def run(self):
        if os.path.exists(TEST_TARGET):
            # Previous run may have failed.
            os.system("rm -rf " + TEST_TARGET)
        os.mkdir(TEST_TARGET)
        deploy(TEST_TARGET, quiet=True)

        self.check(os.system("grep --quiet 'google-analytics' " + \
            os.path.join(TEST_TARGET, "index.html")) == 0,
                   "The deployed index file should contain analytics code")

        # Clean up.
        os.system("rm -rf " + TEST_TARGET)
        return True
