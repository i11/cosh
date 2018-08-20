import logging
import os
import stat
import subprocess

from cosh.misc import Printable


class DockerMount(Printable):
  def __init__(self, source, target, readonly=False):
    self.readonly = readonly
    self.target = target
    self.source = source


class DockerTerminalClient(Printable):

  def run_command(self, image, arguments, **kwargs):
    volume_mounts = ' '.join('%s-v %s:%s'
                             % ('--read-only '
                                if mount.readonly else '', mount.source, mount.target)
                             for mount in kwargs['mounts']) if 'mounts' in kwargs else ''
    envs = ' '.join('-e %s' % env for env in kwargs['environment']) \
      if 'environment' in kwargs else ''
    attachments = ' '.join('-a %s' % a for a in kwargs['attach']) if 'attach' in kwargs else ''
    return 'docker run --net=host -i%s%s%s%s%s%s%s %s %s' % (
      ' %s' % attachments if attachments else '',
      ' -t' if 'tty' in kwargs and kwargs['tty'] else '',
      ' --rm' if 'auto_remove' in kwargs and kwargs['auto_remove'] else '',
      ' %s' % envs if envs else '',
      ' %s' % volume_mounts if volume_mounts else '',
      (' -w %s' % kwargs['working_dir']) if 'working_dir' in kwargs else '',
      ' %s' % kwargs['custom'] if 'custom' in kwargs else '',
      image,
      ' '.join(arguments))

  def run(self, image, arguments, **kwargs):
    cmd = self.run_command(image, arguments, **kwargs)
    logging.debug('Running command:\n%s' % cmd)
    return subprocess.call(cmd, shell=True, close_fds=True, preexec_fn=os.setsid)


class DockerEnvironment(Printable):
  FS_ROOT = '/'
  CONTAINER_HOME = '/home'
  DOCKER_SOCK = '/var/run/docker.sock'

  def __init__(self, tmpdir_base, home):
    self.home = home
    self.tmpdir_base = tmpdir_base

  @classmethod
  def __is_socket(cls, path):
    mode = os.stat(path).st_mode
    return stat.S_ISSOCK(mode)

  @classmethod
  def __root_mount(cls, source, name, destination=None):
    # Create a volume to improve robustness
    target = destination if destination else source
    if source == DockerEnvironment.FS_ROOT:
      logging.warning('%s directory %s is a filesystem root. '
                      'Embedded commands will fail to access it!' % (target, name))
      target = destination if destination else ('/mount/%s' % name)
    return [DockerMount(source=source, target=target)]

  def mounts(self, placed_records, extra_mount={}):
    pwd = os.getcwd()
    dev = '/dev'
    ssh_auth_sock = os.environ.get('SSH_AUTH_SOCK')

    mounts = [DockerMount(source='$(pwd)',
                          target=('/mount/root' if os.getcwd() == DockerEnvironment.FS_ROOT
                                  else '$(pwd)'))]
    if not (pwd == self.tmpdir_base or '$(pwd)' == self.tmpdir_base):
      mounts += DockerEnvironment.__root_mount(self.tmpdir_base, 'tmp')
    if not (pwd == self.home or '$(pwd)' == self.home):
      mounts += DockerEnvironment.__root_mount(self.home, 'home')

    if not self.home == DockerEnvironment.CONTAINER_HOME:
      mounts += DockerEnvironment.__root_mount(self.home, 'home', '/home')

    if DockerEnvironment.__is_socket(DockerEnvironment.DOCKER_SOCK):
      mounts += DockerEnvironment.__root_mount(DockerEnvironment.DOCKER_SOCK, 'docker.sock')

    mounts += DockerEnvironment.__root_mount(dev, 'dev')
    mounts += [
      DockerMount(source=placed_record['path'],
                  target=('/sbin/%s' % placed_record['record'].name),
                  readonly=True)
      for placed_record in placed_records
    ]
    mounts += [DockerMount(source=source, target=target) for source, target in extra_mount.items()]
    if ssh_auth_sock:
      mounts += [DockerMount(source=ssh_auth_sock, target=ssh_auth_sock)]
    return mounts

  def workdir(self):
    return '/mount/root' if os.getcwd() == DockerEnvironment.FS_ROOT else '$(pwd)'

  def environment(self):
    docker_host = os.getenv('DOCKER_HOST',
                            ('unix://%s' % DockerEnvironment.DOCKER_SOCK)
                            if DockerEnvironment.__is_socket(DockerEnvironment.DOCKER_SOCK)
                            else None)

    envs = [
      'HOME=%s' % (
        DockerEnvironment.CONTAINER_HOME if self.home == DockerEnvironment.FS_ROOT else self.home),
      'SSH_AUTH_SOCK'
    ]

    if docker_host:
      envs += ['DOCKER_HOST=%s' % docker_host]
    return envs

  @classmethod
  def create(cls):
    return DockerEnvironment()
