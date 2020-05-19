import base_test
import pandas
import sys

sys.path.append("scripts")
import data_util
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
        # Date normalization
        self.verify_date_normalization("07.04.2020", "2020-04-07")
        self.verify_date_normalization("20/6/2019", "2019-06-20")
        self.verify_date_normalization("2003.3.19", "2003-03-19")

        # Production of "total case counts" data frames.
        geoid_1 = "1.00|1.00"
        geoid_2 = "2.00|2.00"
        geoid_3 = "3.00|3.00"
        geoid_4 = "4.00|4.00"

        date_1 = "2020-04-01"
        date_2 = "2020-04-02"
        date_3 = "2020-04-03"
        date_4 = "2020-04-04"

        in_data = {
            'date': [
                date_2, date_1, date_3, date_2, date_4,
                date_3, date_1, date_1, date_3, date_3,
            ], 'geoid': [
                geoid_3, geoid_3, geoid_2, geoid_4, geoid_2,
                geoid_1, geoid_4, geoid_2, geoid_1, geoid_1,
            ]}
        out_data = data_util.build_case_count_table_from_line_list(
            pandas.DataFrame.from_dict(in_data)).to_dict("records")
        explanation = "The line list data should have been transformed properly"
        self.check(out_data[2][geoid_1] == 3, explanation)
        self.check(out_data[0][geoid_4] == 1, explanation)
        self.check(out_data[0][geoid_1] == 0, explanation)
