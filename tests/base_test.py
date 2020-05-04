from abc import ABC, abstractmethod

class TestFailure(BaseException):
    def __init__(self, explanation):
        self.explanation = explanation

class BaseTest(ABC):

    def __init__(self):
        super().__init__()
        self.failures = []

    @abstractmethod
    def display_name(self):
        pass

    def check(self, condition, explanation):
        if not condition:
            raise TestFailure(explanation)

    def run_wrapper(self):
        try:
            self.run()

        except TestFailure as e:
            self.failures.append(e)

    def tear_down(self):
        for f in self.failures:
            print("\n" + f.explanation + " ")

    def passed(self):
        return len(self.failures) == 0

    @abstractmethod
    def run(self):
        pass
