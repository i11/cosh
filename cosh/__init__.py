import logging
import sys

from cosh.docker import DockerTerminalClient, DockerMount
from cosh.misc import Printable
from cosh.provisioners import DockerProvisioner, CommandsProvisioner


class Cosh(Printable):
  def __init__(self, docker_client, tmpdir, command_base_dir, env, cache, repositories):
    self.docker_client = docker_client
    self.tmpdir = tmpdir
    self.command_base_dir = command_base_dir
    self.env = env
    self.repositories = repositories
    self.cache = cache

  def run(self, command_str, args):
    records = []
    for repository in self.repositories:
      logging.debug('Fetching repository records for: %s' % repository)
      records += [record for record in self.cache.load(repository.list) if
                  record.tags and not record.name == 'docker']
    records = list(set(records))

    logging.debug('Repository records: %s' % records)

    maybe_versioned_command = command_str.split(':')
    command_name = maybe_versioned_command[0]
    logging.debug('Executing command %s with arguments %s' % (command_name, args))

    command_record = None
    for record in records:
      if command_name == record.name:
        command_record = record

    if len(maybe_versioned_command) > 1:
      version = maybe_versioned_command[1]
    elif command_record:
      version = command_record.tags[0]

    if not (command_record and version):
      raise Exception('%s command not found' % command_str)

    placed_records = [
      {
        'record': record,
        'path': ('%s/%s' % (self.command_base_dir, record.name))
      }
      for record in records
    ]

    logging.debug("Provisioning...")
    extra_mounts = DockerProvisioner(self.tmpdir).provision()

    CommandsProvisioner(extra_mounts=extra_mounts,
                        docker_client=self.docker_client,
                        env=self.env,
                        placed_records=placed_records) \
      .provision()

    self.docker_client.run(image='%s:%s' % (command_record.image_name, version),
               arguments=args,
               auto_remove=True,
               environment=self.env.environment(),
               mounts=self.env.mounts(placed_records=placed_records,
                                      extra_mounts=extra_mounts),
               working_dir=self.env.workdir(),
               tty=sys.stdin.isatty())
