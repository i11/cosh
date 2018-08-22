import logging
import os
import time

import jsonpickle

from cosh.misc import Printable


def func_ref_name(fn_ref):
  is_object = '__func__' in fn_ref.__dir__()
  return fn_ref.__func__.__qualname__ if is_object else fn_ref.__qualname__


def func_call(fn_ref, *fn_args):
  is_object = '__func__' in fn_ref.__dir__()
  decrement = 1 if is_object else 0
  fn_arg_size = len(
      fn_ref.__func__.__code__.co_varnames if is_object else fn_ref.__code__.co_varnames) - decrement
  return fn_ref.__call__(*fn_args) if fn_arg_size > 0 else fn_ref.__call__()


class FileCache(Printable):

  def __init__(self, cachedir, ttl=1 * 60 * 60):
    self.cachedir = cachedir
    self.ttl = ttl

  def load(self, fn_ref, *fn_args):
    logging.debug('Loading file cache for %s with %s' % (fn_ref, fn_args))
    file_name = '%s/%s%s.json' % (
      self.cachedir,
      func_ref_name(fn_ref),
      ('_' + '_'.join(fn_args) if fn_args else '')
    )

    if os.path.exists(file_name):
      with open(file_name) as f:
        cache = jsonpickle.decode(f.read())

      if time.time() - cache['timestamp'] > self.ttl or not cache['instance'] == fn_ref.__self__:
        logging.debug('Cache expired. Refreshing...')
        cache = {
          'instance': fn_ref.__self__,
          'result': func_call(fn_ref, *fn_args),
          'timestamp': time.time()
        }
        logging.debug('Writing cache: %s' % cache)
        with open(file_name, 'wb') as f:
          f.write(jsonpickle.encode(cache).encode('utf-8'))
          f.flush()
      else:
        logging.debug('Valid cache found. Loading...')
    else:
      logging.debug('No cache found. Refreshing...')
      cache = {
        'instance': fn_ref.__self__,
        'result': func_call(fn_ref, *fn_args),
        'timestamp': time.time()
      }
      logging.debug('Writing cache: %s' % cache)
      with open(file_name, 'wb') as f:
        f.write(jsonpickle.encode(cache).encode('utf-8'))
        f.flush()
    return cache['result']


class NoCache(Printable):
  def load(self, fn_ref, *fn_args):
    return func_call(fn_ref, *fn_args)
