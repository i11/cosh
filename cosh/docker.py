import logging
import os
import stat
import subprocess

import requests


class DockerReigstryClient:

  def __init__(self, host='registry.hub.docker.com'):
    self.host = host

  def repos(self, organisation='actions'):
    r = requests.get('https://%s/v1/search?q=%s' % (self.host, organisation))
    search = r.json()
    search_results = search['results']
    while search['num_pages'] != search['page']:
      r = requests.get('https://%s/v1/search?q=%s&page=%d'
                       % (self.host, organisation.rstrip('/'), search['page'] + 1))
      search = r.json()
      search_results += search['results']

    return [search_hit for search_hit in search_results
            if search_hit['name'].startswith('%s/' % organisation.rstrip('/'))]

  def tags(self, repo, organisation='actions'):
    r = requests.get('https://%s/v1/repositories/%s/%s/tags'
                     % (self.host, organisation.rstrip('/'), repo))
    return r.json()


class DockerMount:
  def __init__(self, source, target):
    self.target = target
    self.source = source


class DockerTerminalClient:

  def run_command(self, image, arguments=[], environment=[], mounts=[], working_dir=None,
                  auto_remove=True, tty=False):
    return 'docker run --net=host -i %s %s %s %s %s %s %s' % (
      '-t' if tty else '',
      '--rm' if auto_remove else '',
      ' '.join('-e %s' % env for env in environment),
      ' '.join('-v %s:%s' % (mount.source, mount.target) for mount in mounts),
      ('-w %s' % working_dir) if working_dir else '',
      image,
      ' '.join(arguments))

  def run(self, image, arguments=[], environment=[], mounts=[], working_dir=None, auto_remove=True):
    cmd = self.run_command(image, arguments, environment, mounts, working_dir, auto_remove,
                           tty=True)
    logging.debug('Running command:\n%s' % cmd)
    return subprocess.check_call(cmd.split(' '))


class DockerEnvironment:
  FS_ROOT = '/'
  CONTAINER_HOME = '/home'
  DOCKER_SOCK = '/var/run/docker.sock'

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

  def mounts(self, provisioning, extra_mount={}):
    home = os.environ.get('HOME')
    pwd = os.getcwd()
    dev = '/dev'

    mounts = DockerEnvironment.__root_mount(pwd, 'root')
    # if not pwd == tmp:
    #   mounts += Environment.__root_mount(tmp, 'tmp')
    if not pwd == home:
      mounts += DockerEnvironment.__root_mount(home, 'home')

    if not home == DockerEnvironment.CONTAINER_HOME:
      mounts += DockerEnvironment.__root_mount(home, 'home', '/home')

    if DockerEnvironment.__is_socket(DockerEnvironment.DOCKER_SOCK):
      mounts += DockerEnvironment.__root_mount(DockerEnvironment.DOCKER_SOCK, 'docker.sock')

    mounts += DockerEnvironment.__root_mount(dev, 'dev')

    # TODO: mount read-only!
    mounts += [DockerMount(source=source, target='/sbin/%s' % command)
               for command, source in provisioning.items()]

    mounts += [DockerMount(source=source, target=target) for source, target in extra_mount]

    return mounts

  def workdir(self):
    pwd = os.getcwd()
    return '/mount/root' if pwd == DockerEnvironment.FS_ROOT else pwd

  def environment(self):
    home = os.environ.get('HOME')
    docker_host = os.getenv('DOCKER_HOST',
                            ('unix://%s' % DockerEnvironment.DOCKER_SOCK)
                            if DockerEnvironment.__is_socket(DockerEnvironment.DOCKER_SOCK)
                            else None)

    envs = [
      'HOME=%s' % (DockerEnvironment.CONTAINER_HOME if home == DockerEnvironment.FS_ROOT else home)
    ]

    if docker_host:
      envs += ['DOCKER_HOST=%s' % docker_host]
    return envs

  @classmethod
  def create(cls):
    return DockerEnvironment()
