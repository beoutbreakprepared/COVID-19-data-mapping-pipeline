from abc import ABC, abstractmethod

class BaseTest(ABC):

  def __init__(self):
    super().__init__()

  @abstractmethod
  def display_name(self):
    pass

  @abstractmethod
  def run(self):
    pass
