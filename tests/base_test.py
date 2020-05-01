from abc import ABC, abstractmethod

class TestFailure(BaseException):
    def __init__(self, explanation):
        self.explanation = explanation

class BaseTest(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def display_name(self):
        pass

    def check(self, condition, explanation):
        if not condition:
            raise TestFailure(explanation)

    def run_wrapper(self):
        try:
            self.run()
            return True
        except TestFailure as e:
            print("\n" + e.explanation + " ", end="")
            return False

    @abstractmethod
    def run(self):
        pass
