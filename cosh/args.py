import argparse
import logging
import os

from cosh import Cosh, Tmpdir
from cosh.cache import FileCache, NoCache
from cosh.docker import DockerEnvironment
from cosh.docker.repositories import DockerRepositoryFactory
from cosh.lock import Mutex


def get():
  parser = argparse.ArgumentParser(description='Container shell', prog='cosh')
  parser.add_argument('--home', default=os.environ.get('HOME'), type=str,
                      help='Set home path to be mounted for containers')
  parser.add_argument('--tmpdir', default=Tmpdir.default_instance().base(), type=str,
                      help='Set tmp path to be mounted for containers')
  parser.add_argument('--debug', dest='debug', action='store_true', help='Turn on debug logging')
  parser.add_argument('--cache-dir', type=str, required=False,
                      help='Repository record cache directory')
  parser.add_argument('--no-cache', dest='cache', action='store_false', help='Ignore cache')
  parser.add_argument('--lock-ttl', default=1 * 60 * 60, type=int,
                      help='Execution lock ttl in seconds')
  parser.add_argument('-r', '--repository', dest='repositories',
                      type=str, required=False, action='append',
                      help='Docker image repository that will be used as a prefix.'
                           ' Multiple values are allowed.'
                           ' The first value takes the precedence for images with the same name.')
  parser.add_argument('-v', '--volume', default=[], dest='volumes',
                      type=str, required=False, action='append',
                      help='Extra docker volumes to be mounted for containers. '
                           ' Multiple values are allowed.'
                           ' Format: source:destination. Example: -v /opt:/home/opt')
  parser.add_argument('-e', '--env', default=[], dest='envs',
                      type=str, required=False, action='append',
                      help='Extra docker environments to be set for containers. '
                           ' Multiple values are allowed.'
                           ' Format: KEY=VALUE. Example: -e MY_VAR=foo')
  parser.add_argument('--gcr-key-file', type=str, required=False,
                      help='GCR key file that would be used if gcr.io repository was provided')

  parser.add_argument('command', type=str,
                      help='Command to execute')
  parser.add_argument('arguments', type=str, nargs=argparse.REMAINDER,
                      help='Command arguments')

  parser.set_defaults(debug=False)
  parser.set_defaults(cache=True)

  args = parser.parse_args()

  if args.debug:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.INFO)

  tmpdir = Tmpdir(basedir=args.tmpdir, cachedir=args.cache_dir)

  logging.debug('Locking...')
  mutex = Mutex(tmpdir=tmpdir.tmp(), ttl=args.lock_ttl)
  mutex.lock()

  volumes = {volume.split(':')[0]: volume.split(':')[1] for volume in args.volumes}

  if not args.repositories:
    args.repositories = ['actions/']

  cache = FileCache(tmpdir=tmpdir) if args.cache else NoCache()

  logging.debug('Got repositories: %s' % args.repositories)
  repositories = [DockerRepositoryFactory(repository, args.gcr_key_file).versions().pop()
                  for repository in args.repositories]

  cosh = Cosh(tmpdir=tmpdir,
              env=DockerEnvironment(tmpdir_base=args.tmpdir,
                                    home=args.home,
                                    extra_volumes=volumes,
                                    extra_envs=args.envs),
              cache=cache,
              repositories=repositories)
  cosh.run_checks()

  try:
    cosh.run(args.command, args.arguments)
  except BaseException as e:
    if isinstance(e, KeyboardInterrupt):
      logging.error('Interrupting...')
    else:
      logging.error(e)
    logging.debug('Unlocking...')
    mutex.unlock()
  else:
    logging.debug('Unlocking...')
    mutex.unlock()
