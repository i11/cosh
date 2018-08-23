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

  def __init__(self, docker_binary='docker'):
    self.docker_binary = docker_binary

  def run_command(self, image, arguments, **kwargs):
    volume_mounts = ' '.join('%s-v %s:%s'
                             % ('--read-only '
                                if mount.readonly else '', mount.source, mount.target)
                             for mount in kwargs['mounts']) if 'mounts' in kwargs else ''
    envs = ' '.join('-e %s' % env for env in kwargs['environment']) \
      if 'environment' in kwargs else ''
    attachments = ' '.join('-a %s' % a for a in kwargs['attach']) if 'attach' in kwargs else ''
    return '%s run --net=host -i%s%s%s%s%s%s%s %s %s' % (
      self.docker_binary,
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

  def __init__(self, tmpdir_base, home, extra_volumes, extra_envs):
    self.extra_envs = extra_envs
    self.extra_volumes = extra_volumes
    self.home = home
    self.tmpdir_base = tmpdir_base

  @classmethod
  def __is_socket(cls, path):
    return stat.S_ISSOCK(os.stat(path).st_mode) if os.path.exists(path) else False

  @classmethod
  def __root_mount(cls, source, name, destination=None):
    # Create a volume to improve robustness
    target = destination if destination else source
    if source == DockerEnvironment.FS_ROOT:
      logging.warning('%s directory %s is a filesystem root. '
                      'Embedded commands will fail to access it!' % (target, name))
      target = destination if destination else ('/mount/%s' % name)
    return [DockerMount(source=source, target=target)]

  def mounts(self, placed_records, extra_mounts={}):
    __extra_mounts = {}
    __extra_mounts.update(extra_mounts)
    __extra_mounts.update(self.extra_volumes)

    logging.debug('Extra mounts: %s' % __extra_mounts)

    pwd = os.getcwd()
    dev = '/dev'
    ssh_auth_sock = os.environ.get('SSH_AUTH_SOCK')

    mounts = [DockerMount(source=pwd, target=self.workdir())]
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
    mounts += [DockerMount(source=source, target=target)
               for source, target in __extra_mounts.items()]
    if ssh_auth_sock:
      mounts += [DockerMount(source=ssh_auth_sock, target=ssh_auth_sock)]
    return mounts

  def workdir(self):
    pwd = os.getcwd()
    return '/mount/root' if pwd == DockerEnvironment.FS_ROOT else pwd

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

    # TODO: This is ugly. Redo! Maybe dit instead of string list
    merged_envs = [] + self.extra_envs
    for env in envs:
      env_split = env.split('=')
      if self.extra_envs:
        for extra_env in self.extra_envs:
          extra_env_split = extra_env.split('=')
          value = (extra_env_split[1] if len(extra_env_split) > 1 else None) \
            if extra_env_split[0] == env_split[0] \
            else (env_split[1] if len(env_split) > 1 else None)
          merged_envs += [
            '%s%s' % (env_split[0], ('=%s' % os.path.expandvars(value) if value else ''))
          ]
      else:
        merged_envs += [os.path.expandvars(env)]

    logging.debug('Merged envs: %s' % merged_envs)
    distinct_envs = list(set(merged_envs))
    logging.debug('Distinct envs: %s' % distinct_envs)
    return distinct_envs

  @classmethod
  def create(cls):
    return DockerEnvironment()
