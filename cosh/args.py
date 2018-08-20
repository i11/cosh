import argparse
import logging
import os

from cosh import Cosh, Tmpdir
from cosh.cache import FileCache, NoCache
from cosh.docker import DockerEnvironment
from cosh.docker.repositories import DockerRepositoryFactory


def get():
  parser = argparse.ArgumentParser(description='Container shell', prog='cosh')
  parser.add_argument('--home', default=os.environ.get('HOME'), type=str,
                      help='Set home path to be mounted for containers')
  parser.add_argument('--tmpdir', default=Tmpdir.default_instance().base(), type=str,
                      help='Set tmp path to be mounted for containers')
  parser.add_argument('--debug', dest='debug', action='store_true', help='Turn on debug logging')
  parser.add_argument('--no-cache', dest='cache', action='store_false', help='Ignore cache')
  parser.add_argument('-r', '--repository', type=str, required=False, action='append',
                      help='Docker image repository that will be used as a prefix.'
                           ' Multiple values are supported.'
                           ' The first value takes the precedence for images with the same name.')
  parser.add_argument('command', type=str,
                      help='Command to execute')
  parser.add_argument('arguments', type=str, nargs=argparse.REMAINDER,
                      help='Command arguments')

  parser.set_defaults(debug=False)
  parser.set_defaults(cache=True)

  args = parser.parse_args()

  if not args.repository:
    args.repository = ['actions/']

  if args.debug:
    logging.basicConfig(level=logging.DEBUG)
  else:
    logging.basicConfig(level=logging.INFO)

  tmpdir = Tmpdir(args.tmpdir)

  cache = FileCache(tmpdir=tmpdir) if args.cache else NoCache()

  logging.debug('Got repositories: %s' % args.repository)
  repositories = [DockerRepositoryFactory(repo).versions().pop() for repo in args.repository]

  cosh = Cosh(tmpdir=tmpdir,
              env=DockerEnvironment(tmpdir_base=args.tmpdir, home=args.home),
              cache=cache,
              repositories=repositories)
  cosh.run_checks()
  cosh.run(args.command, args.arguments)
