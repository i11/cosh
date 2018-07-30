import logging

from cosh.docker import DockerReigstryClient, DockerTerminalClient, DockerMount
from cosh.provisioners import DockerProvisioner, CommandsProvisioner
from cosh.requirements import DockerRequirement
from cosh.tmpdir import Tmpdir


class Cosh():
  def __init__(self, env, cache, prefix, reqs=[]):
    self.env = env
    self.prefix = ('%s/' % prefix.rstrip('/')) if prefix else ''
    self.reqs = reqs
    self.cache = cache
    self.registry = DockerReigstryClient()
    self.tmpdir = Tmpdir()

  def latest_version(self, command):
    tags = self.registry.tags(command, organisation=self.prefix)
    for tag in tags:
      if tag['name'] == 'latest':
        return 'latest'
    return tags[0]['name'] if tags else None

  def remote_commands(self):
    return [repo['name'].split('/')[1] for repo in self.registry.repos(self.prefix)]

  def run_checks(self):
    for req in ([DockerRequirement()] + self.reqs):
      req.check()

  def run(self, command_str, args):
    logging.debug('Fetching all remote commands...')
    remote_commands = [command for command in self.cache.load(self.remote_commands) if
                       not command in ['docker']]
    versioned_commands = {command: self.cache.load(self.latest_version, command) for command in
                          remote_commands if self.cache.load(self.latest_version, command)}

    maybe_versioned_command = command_str.split(':')
    command_name = maybe_versioned_command[0]
    logging.debug('Executing command %s with arguments %s' % (command_name, args))

    version = maybe_versioned_command[1] \
      if len(maybe_versioned_command) > 1 else versioned_commands[command_name]

    if not (command_name in remote_commands and version):
      raise Exception('%s command not found' % command_str)

    logging.debug("Provisioning...")
    provisioning = {}

    docker_prov = DockerProvisioner(self.tmpdir.tmp())
    provisioning.update(docker_prov.provision())

    docker = DockerTerminalClient()

    commands_prov = CommandsProvisioner(tmp=self.tmpdir.base(),
                                        docker=docker,
                                        env=self.env,
                                        basedir=self.tmpdir.bin(),
                                        prefix=self.prefix,
                                        versioned_commands=versioned_commands)
    provisioning.update(commands_prov.provision())

    docker.run(image='%s%s:%s' % (self.prefix, command_name, version),
               arguments=args,
               auto_remove=True,
               environment=self.env.environment(),
               mounts=self.env.mounts(tmp=self.tmpdir.base(), provisioning=provisioning),
               working_dir=self.env.workdir(),
               tty=True)
