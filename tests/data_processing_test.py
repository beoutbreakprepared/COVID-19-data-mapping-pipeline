import base_test
import os
import sys

sys.path.append("scripts")
import split

class DataProcessingTest(base_test.BaseTest):
    def display_name(self):
        return "Data processing tests"

    def verify_date_normalization(self, input_date, expected):
        actual = split.normalize_date(input_date)
        self.check(expected == split.normalize_date(input_date),
                   "Normalizing date '" + input_date + "' should yield "
                   "'" + expected + "', not '" + actual + "'")

    def run(self):
        self.verify_date_normalization("07.04.2020", "2020-04-07")
        self.verify_date_normalization("20/6/2019", "2019-06-20")
        self.verify_date_normalization("2003.3.19", "2003-03-19")
