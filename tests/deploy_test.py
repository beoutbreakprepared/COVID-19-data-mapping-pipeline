import base_test
import sys

sys.path.append("scripts")
import deploy

class DeployTest(base_test.BaseTest):
    def display_name(self):
        return "Deployment tests"

    def run(self):
        return False
