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
        os.mkdir(TEST_TARGET)
        deploy(TEST_TARGET, quiet=True)
        os.system("rm -rf " + TEST_TARGET)
        return True
