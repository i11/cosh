import logging
import sys

from cosh.docker import DockerTerminalClient, DockerMount
from cosh.misc import Printable
from cosh.provisioners import DockerProvisioner, CommandsProvisioner
from cosh.requirements import DockerRequirement
from cosh.tmpdir import Tmpdir


class Cosh(Printable):
  def __init__(self, tmpdir, env, cache, repositories, reqs=[]):
    self.tmpdir = tmpdir
    self.env = env
    self.repositories = repositories
    self.reqs = reqs
    self.cache = cache

  def repository_records(self):
    return list(
        set([record for repo in self.repositories for record in repo.list()
             if record.tags and not record.name == 'docker']
            ))

  def run_checks(self):
    for req in ([DockerRequirement()] + self.reqs):
      req.check()

  def run(self, command_str, args):
    logging.debug('Fetching all repository records...')
    repository_records = self.cache.load(self.repository_records)
    logging.debug('Repository records: %s' % repository_records)

    maybe_versioned_command = command_str.split(':')
    command_name = maybe_versioned_command[0]
    logging.debug('Executing command %s with arguments %s' % (command_name, args))

    command_record = None
    for record in repository_records:
      if command_name == record.name:
        command_record = record

    if len(maybe_versioned_command) > 1:
      version = maybe_versioned_command[1]
    elif command_record:
      version = command_record.tags[0]

    if not (command_record and version):
      raise Exception('%s command not found' % command_str)

    placed_records = [
      {'record': record, 'path': ('%s/%s' % (self.tmpdir.bin().rstrip('/'), record.name))}
      for record in repository_records
    ]

    logging.debug("Provisioning...")
    extra_mounts = DockerProvisioner(self.tmpdir.tmp()).provision()

    docker = DockerTerminalClient()

    CommandsProvisioner(extra_mounts=extra_mounts,
                        docker=docker,
                        env=self.env,
                        placed_records=placed_records) \
      .provision()

    docker.run(image='%s:%s' % (command_record.image_name, version),
               arguments=args,
               auto_remove=True,
               environment=self.env.environment(),
               mounts=self.env.mounts(placed_records=placed_records,
                                      extra_mounts=extra_mounts),
               working_dir=self.env.workdir(),
               tty=sys.stdin.isatty())

  def __eq__(self, other):
    return isinstance(other, self.__class__) \
           and ((self.tmpdir, self.repositories, self.cache)
                == (other.tmpdir, other.repositories, other.cache))

  def __ne__(self, other):
    return ((self.tmpdir, self.repositories, self.cache)
            != (other.tmpdir, other.repositories, other.cahe))

  def __lt__(self, other):
    return ((self.tmpdir, self.repositories, self.cache)
            < (other.tmpdir, other.repositories, other.cahe))

  def __le__(self, other):
    return ((self.tmpdir, self.repositories, self.cache)
            <= (other.tmpdir, other.repositories, other.cahe))

  def __gt__(self, other):
    return ((self.tmpdir, self.repositories, self.cache)
            > (other.tmpdir, other.repositories, other.cahe))

  def __ge__(self, other):
    return ((self.tmpdir, self.repositories, self.cache)
            >= (other.tmpdir, other.repositories, other.cahe))

  def __hash__(self):
    return hash((self.tmpdir, self.repositories, self.cache))
