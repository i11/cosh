import logging
import os
import stat

import requests


class DockerReigstryClient:

  def __init__(self, hub='registry.hub.docker.com',
               store='store.docker.com'):
    self.store = store
    self.hub = hub

  def list_store_repos(self, organisation='actions'):
    r = requests.get('https://%s/v2/repositories/%s?page_size=100' % (self.store, organisation))
    repos = r.json()
    results = repos['results']
    while repos['next']:
      r = requests.get(repos['next'])
      repos = r.json()
      results += repos['results']
    return results

  def search_hub(self, organisation='actions'):
    r = requests.get('https://%s/v1/search?q=%s' % (self.hub, organisation))
    search = r.json()
    search_results = search['results']
    while search['num_pages'] != search['page']:
      r = requests.get('https://%s/v1/search?q=%s&page=%d'
                       % (self.hub, organisation, search['page'] + 1))
      search = r.json()
      search_results += search['results']

    return [search_hit for search_hit in search_results
            if search_hit['name'].startswith('%s/' % organisation.rstrip('/'))]

  def tags(self, repo, organisation='actions'):
    r = requests.get('https://%s/v1/repositories/%s/%s/tags'
                     % (self.hub, organisation.rstrip('/'), repo))
    return r.json()


class DockerMount:
  def __init__(self, source, target, readonly=False):
    self.readonly = readonly
    self.target = target
    self.source = source


class DockerTerminalClient:

  def run_command(self,
                  image,
                  arguments,
                  **kwargs):
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

  def run(self,
          image,
          arguments,
          **kwargs):
    cmd = self.run_command(image, arguments, **kwargs)
    logging.debug('Running command:\n%s' % cmd)
    return os.system(cmd)


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

  def mounts(self, tmp, provisioning, extra_mount={}):
    home = os.environ.get('HOME')
    pwd = os.getcwd()
    dev = '/dev'

    mounts = DockerEnvironment.__root_mount(pwd, 'root')
    if not pwd == tmp:
      mounts += DockerEnvironment.__root_mount(tmp, 'tmp')
    if not pwd == home:
      mounts += DockerEnvironment.__root_mount(home, 'home')

    if not home == DockerEnvironment.CONTAINER_HOME:
      mounts += DockerEnvironment.__root_mount(home, 'home', '/home')

    if DockerEnvironment.__is_socket(DockerEnvironment.DOCKER_SOCK):
      mounts += DockerEnvironment.__root_mount(DockerEnvironment.DOCKER_SOCK, 'docker.sock')

    mounts += DockerEnvironment.__root_mount(dev, 'dev')

    mounts += [DockerMount(source=source, target='/sbin/%s' % command, readonly=True)
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
