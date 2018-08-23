import argparse
import logging
import os
from random import Random

from cosh import Cosh
from cosh.cache import FileCache, NoCache
from cosh.docker import DockerTerminalClient, DockerEnvironment
from cosh.docker.repositories import DockerRepositoryFactory
from cosh.tmpdir import Tmpdir, rmdir


def normalize_path(path):
  return os.path.abspath(os.path.expanduser(os.path.expandvars(path)))


def get():
  parser = argparse.ArgumentParser(description='Container shell', prog='cosh')
  parser.add_argument('--home', default=os.environ.get('HOME'), type=str,
                      help='Set home path to be mounted for containers')
  parser.add_argument('--tmpdir', default=Tmpdir.default_instance().base(), type=str,
                      help='Set tmp path to be mounted for containers')
  parser.add_argument('--debug', dest='debug', action='store_true', help='Turn on debug logging')
  parser.add_argument('--docker-binary', default='docker', type=str, help='Docker binary path')
  parser.add_argument('--cache-dir', type=str, required=False,
                      help='Repository record cache directory')
  parser.add_argument('--no-cache', dest='cache', action='store_false', help='Ignore cache')
  parser.add_argument('--cache-ttl', default=6 * 60 * 60, type=int,
                      help='Repository cache ttl in seconds')
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

  # TODO: Redesign
  tmpdir = Tmpdir(basedir=normalize_path(args.tmpdir),
                  cachedir=normalize_path(args.cache_dir) if args.cache_dir else None)

  volumes = {
    normalize_path(volume.split(':')[0]): normalize_path(volume.split(':')[1])
    for volume in args.volumes
  }

  if not args.repositories:
    args.repositories = ['actions/']

  cache = FileCache(cachedir=tmpdir.cache(), ttl=args.cache_ttl) if args.cache else NoCache()

  logging.debug('Got repositories: %s' % args.repositories)
  repositories = [DockerRepositoryFactory(repository.strip(), args.gcr_key_file).versions().pop()
                  for repository in args.repositories]

  maybe_versioned_command = args.command.split(':')
  command_name = maybe_versioned_command[0]
  command_base_dir = '%s/%s.%d' \
                     % (tmpdir.bin().rstrip('/'), command_name, Random().randint(10000, 99999))
  logging.debug('Creating command base dir: %s' % command_base_dir)
  if not os.path.exists(command_base_dir):
    os.makedirs(command_base_dir)

  docker_client = DockerTerminalClient(os.path.expanduser(os.path.expandvars(args.docker_binary)))

  cosh = Cosh(docker_client=docker_client,
              tmpdir=tmpdir.tmp(),
              command_base_dir=command_base_dir,
              env=DockerEnvironment(tmpdir_base=tmpdir.base(),
                                    home=normalize_path(args.home),
                                    extra_volumes=volumes,
                                    extra_envs=args.envs),
              cache=cache,
              repositories=repositories)

  logging.debug('Running cosh: %s' % cosh)
  try:
    cosh.run(args.command, args.arguments)
  except BaseException as e:
    if isinstance(e, KeyboardInterrupt):
      logging.error('Interrupting...')
    else:
      logging.error(e)

  logging.debug('Cleaning up: %s' % command_base_dir)
  rmdir(command_base_dir)
