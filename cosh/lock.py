import errno
import logging
import os
import time


class Mutex:
  def __init__(self, tmpdir, ttl=1 * 60 * 60):
    self.ttl = ttl
    self.unlocked = '%s/%s' % (tmpdir.rstrip('/'), '.unlocked')
    self.locked = '%s/%s' % (tmpdir.rstrip('/'), '.locked')

  def lock(self):
    try:
      os.rename(self.unlocked, self.locked)
      os.utime(self.locked)
    except OSError as e:
      if e.errno == errno.EEXIST:
        raise Exception('Both lock and unlock present. Something went horribly wrong...')
      elif e.errno == errno.ENOENT:
        try:
          ctime = os.path.getctime(self.locked)
          if time.time() - ctime > self.ttl:
            logging.warning('Lock is too old. Taking over...')
            self.unlock()
            self.lock()
          else:
            raise Exception('Already locked. Wait and try again...')
        except FileNotFoundError as fnfe:
          logging.debug('Seems like a fresh start. Creating a lock...')
          open(self.locked, 'a').close()
      else:
        raise Exception('Unknown error: %s' % e)

  def unlock(self):
    try:
      os.rename(self.locked, self.unlocked)
    except OSError as e:
      if e.errno == errno.EEXIST:
        raise Exception('Both lock and unlock present. Something went horribly wrong...')
      elif e.errno == errno.ENOENT:
        logging.warning('Already unlocked. Resetting...')
      else:
        raise Exception('Unknown error: %s' % e)
