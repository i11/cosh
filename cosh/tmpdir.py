import os
import platform
import tempfile


class Tmpdir:

  @classmethod
  def __create(cls, __dir):
    if not os.path.exists(__dir):
      os.makedirs(__dir)

  def __init__(self):
    self.__basedir = \
      ('/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()).rstrip('/')
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
