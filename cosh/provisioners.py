import hashlib
import logging
import os
import stat
import tarfile

import requests


def download_file(url, filename):
  r = requests.get(url, stream=True)
  with open(filename, 'wb') as f:
    for chunk in r.iter_content(chunk_size=65536):
      if chunk:  # filter out keep-alive new chunks
        f.write(chunk)
  return filename


def sha256_checksum(filename, block_size=65536):
  sha256 = hashlib.sha256()
  with open(filename, 'rb') as f:
    for block in iter(lambda: f.read(block_size), b''):
      sha256.update(block)
  return sha256.hexdigest()


class DockerProvisioner:
  __docker_static_url = 'https://download.docker.com/linux/static/stable/x86_64/' \
                        'docker-18.06.0-ce.tgz'
  __docker_static_sha256 = '1c2fa625496465c68b856db0ba850eaad7a16221ca153661ca718de4a2217705'

  def __init__(self, basedir):
    self.basedir = basedir

  def provision(self):
    target = '%s/docker/docker' % self.basedir

    logging.debug('Provisioning docker %s...' % target)
    if not os.path.exists(target):
      local_docker_tgz = '%s/docker.tgz' % self.basedir
      download_file(DockerProvisioner.__docker_static_url, local_docker_tgz)
      if sha256_checksum(local_docker_tgz) == DockerProvisioner.__docker_static_sha256:
        docker_tgz = tarfile.open(local_docker_tgz, 'r')
        docker_tgz.extractall(self.basedir, members=[member for member in docker_tgz.getmembers()])
      else:
        raise Exception('sha256 mismatch for %s' % local_docker_tgz)
    return {'docker': target}


class CommandsProvisioner:

  def __init__(self, docker, env, basedir, prefix, versioned_commands):
    self.docker = docker
    self.env = env
    self.prefix = prefix
    self.versioned_commands = versioned_commands
    self.basedir = basedir
    self.command_provisioning = {command: '%s/%s' % (self.basedir.rstrip('/'), command)
                                 for command, version in self.versioned_commands.items()}

  def provision(self):
    targets = {}
    logging.debug('Provisioning commands: %s' % self.versioned_commands)

    for command, version in self.versioned_commands.items():
      logging.debug('Provisioning command: %s:%s' % (command, version))
      file_name = '%s/%s' % (self.basedir, command)
      if not os.path.exists(file_name):
        file = open(file_name, 'w')
        file.write('#!/bin/bash\n'
                   'set -Eeuo pipefail\n'
                   '%s'
                   % self.docker.run_command(image='%s%s:%s' % (self.prefix, command, version),
                                             arguments=["$@"],
                                             auto_remove=True,
                                             environment=self.env.environment(),
                                             mounts=self.env.mounts(self.command_provisioning),
                                             working_dir=self.env.workdir(),
                                             tty=False))
        file.close()
        st = os.stat(file_name)
        os.chmod(file_name, st.st_mode | stat.S_IEXEC)

      logging.debug('Add command %s to %s target' % (command, file_name))
      targets.update(dict([(command, file_name)]))
    return targets
