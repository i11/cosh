import os
import platform
import tempfile

from cosh.misc import Printable


class Tmpdir(Printable):
  @classmethod
  def __create(cls, __dir):
    if not os.path.exists(__dir):
      os.makedirs(__dir)

  @classmethod
  def default_instance(cls):
    return Tmpdir(('/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()).rstrip('/'))

  def __init__(self, basedir):
    self.__basedir = basedir
    self.__tmpdir = '%s/cosh' % self.__basedir
    self.__bindir = '%s/bin' % self.__tmpdir
    self.__cachedir = '%s/cache' % self.__tmpdir

  def base(self):
    return self.__basedir

  def tmp(self):
    Tmpdir.__create(self.__tmpdir)
    return self.__tmpdir

  def bin(self):
    Tmpdir.__create(self.__bindir)
    return self.__bindir

  def cache(self):
    Tmpdir.__create(self.__cachedir)
    return self.__cachedir
