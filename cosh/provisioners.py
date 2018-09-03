import hashlib
import logging
import os
import stat
import tarfile

import requests

from cosh.misc import Printable


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


class DockerProvisioner(Printable):
  __docker_static_url = 'https://download.docker.com/linux/static/stable/x86_64/' \
                        'docker-18.06.0-ce.tgz'
  __docker_static_sha256 = '1c2fa625496465c68b856db0ba850eaad7a16221ca153661ca718de4a2217705'

  def __init__(self, tmpdir):
    self.tmpdir = tmpdir

  def provision(self):
    target = '%s/docker/docker' % self.tmpdir

    logging.debug('Provisioning docker %s...' % target)
    if not os.path.exists(target):
      local_docker_tgz = '%s/docker.tgz' % self.tmpdir
      download_file(DockerProvisioner.__docker_static_url, local_docker_tgz)
      if sha256_checksum(local_docker_tgz) == DockerProvisioner.__docker_static_sha256:
        docker_tgz = tarfile.open(local_docker_tgz, 'r')
        docker_tgz.extractall(self.tmpdir, members=[member for member in docker_tgz.getmembers()])
        os.remove(local_docker_tgz)
      else:
        raise Exception('sha256 mismatch for %s' % local_docker_tgz)
    return {target: '/sbin/docker'}


class CommandsProvisioner(Printable):

  def __init__(self, extra_mounts, docker_client, env, placed_records):
    self.extra_mounts = extra_mounts
    self.docker_client = docker_client
    self.env = env
    self.placed_records = placed_records

  def provision(self):
    logging.debug('Provisioning commands: %s' % self.placed_records)
    # login_flag = ' -l' if self.interactive else ''

    for placed_record in self.placed_records:
      logging.debug('Provisioning command: %s:%s' % (
        placed_record['record'].name, placed_record['record'].tags[0]))
      file = open(placed_record['path'], 'w')
      # why test -t 0 instead test -t 1:
      # Specifying -t is forbidden when the client is receiving its standard input from a pipe
      file.write(
          '#!/bin/bash -e\n'
          'cmd=$(basename ${BASH_SOURCE[0]})\n'
          'test -x /sbin.orig/$cmd && exec /sbin.orig/$cmd "$@"\n'
          'test -x /bin/$cmd && exec /bin/$cmd "$@"\n'
          'test -t 0 && export USE_TTY="-t"\n'
          'exec %s'
          % (self.docker_client.run_command(image='%s:%s' % (
            placed_record['record'].image_name, placed_record['record'].tags[0]),
                                            arguments=["$@"],
                                            auto_remove=True,
                                            environment=self.env.environment(),
                                            mounts=self.env.mounts(extra_mounts=self.extra_mounts,
                                                                   placed_records=self.placed_records),
                                            working_dir=self.env.workdir(),
                                            custom='${USE_TTY}')))
      file.close()
      st = os.stat(placed_record['path'])
      os.chmod(placed_record['path'], st.st_mode | stat.S_IEXEC)
