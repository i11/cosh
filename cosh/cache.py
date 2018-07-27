import codecs
import json
import logging
import os
import time

from cosh.tmpdir import Tmpdir


def func_ref_name(fn_ref):
  is_object = '__func__' in fn_ref.__dir__()
  return fn_ref.__func__.__qualname__ if is_object else fn_ref.__qualname__


def func_call(fn_ref, *fn_args):
  is_object = '__func__' in fn_ref.__dir__()
  decrement = 1 if is_object else 0
  fn_arg_size = len(
    fn_ref.__func__.__code__.co_varnames if is_object else fn_ref.__code__.co_varnames) - decrement
  return fn_ref.__call__(*fn_args) if fn_arg_size > 0 else fn_ref.__call__()


class FileCache:

  def __init__(self, ttl=10 * 60):
    self.ttl = ttl
    self.tmpdir = Tmpdir()

  def load(self, fn_ref, *fn_args):
    logging.debug('Loading file cache for %s with %s' % (fn_ref, fn_args))
    file_name = '%s/%s%s.json' % (
      self.tmpdir.cache(), func_ref_name(fn_ref), ('_' + '_'.join(fn_args) if fn_args else ''))

    if os.path.exists(file_name):
      ctime = os.path.getctime(file_name)
      if time.time() - ctime > self.ttl:
        logging.debug('Cache expired. Refreshing...')
        result = func_call(fn_ref, *fn_args)
        logging.debug('Writing results: %s' % result)
        with open(file_name, 'wb') as f:
          json.dump(result, codecs.getwriter('utf-8')(f), ensure_ascii=False)
      else:
        logging.debug('Valid cache found. Loading...')
        with open(file_name) as f:
          result = json.load(f)
    else:
      logging.debug('No cache found. Refreshing...')
      result = func_call(fn_ref, *fn_args)
      logging.debug('Writing results: %s' % result)
      with open(file_name, 'wb') as f:
        json.dump(result, codecs.getwriter('utf-8')(f), ensure_ascii=False)
    return result


class NoCache:
  def load(self, fn_ref, *fn_args):
    return func_call(fn_ref, *fn_args)
