import argparse
import logging

from cosh import Cosh
from cosh.cache import FileCache, NoCache
from cosh.docker import DockerEnvironment


def get():
  parser = argparse.ArgumentParser(description='Container shell', prog='cosh')

  parser.add_argument('--debug', dest='debug', action='store_true', help='Turn on debug logging')
  parser.add_argument('--no-cache', dest='cache', action='store_false', help='Ignore cache')
  # TODO: Support multiple prefixes
  parser.add_argument('--image-prefix', type=str, required=False,
                      default='actions/',
                      help='Docker image name prefix that will be used to prefix '
                           'all given command names')
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

  cache = FileCache() if args.cache else NoCache()

  cosh = Cosh(env=DockerEnvironment(),
              cache=cache,
              prefix=args.image_prefix)
  cosh.run_checks()
  cosh.run(args.command, args.arguments)
