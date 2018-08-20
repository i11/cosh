class Printable:
  def __repr__(self):
    return str(self.__class__) + ": " + str(self.__dict__)

  def __eq__(self, other):
    return self.__dict__ == other.__dict__
