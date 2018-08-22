import os
import pathlib
import platform
import tempfile

from cosh.misc import Printable


def rmdir(dir):
  dir = pathlib.Path(dir)
  for item in dir.iterdir():
    if item.is_dir():
      rmdir(item)
    else:
      item.unlink()
  dir.rmdir()


class Tmpdir(Printable):
  @classmethod
  def __create(cls, __dir):
    if not os.path.exists(__dir):
      os.makedirs(__dir)

  @classmethod
  def default_instance(cls):
    basedir = ('/tmp' if platform.system() == 'Darwin' else tempfile.gettempdir()).rstrip('/')
    return Tmpdir(basedir)

  def __init__(self, basedir, cachedir=None):
    self.__basedir = basedir
    self.__tmpdir = '%s/cosh' % self.__basedir
    self.__bindir = '%s/bin' % self.__tmpdir
    self.__cachedir = cachedir if cachedir else '%s/cache' % self.__tmpdir

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
