import logging
import re
import warnings

import google.auth
import google.auth.transport.requests
import requests
from google.oauth2 import service_account
from natsort import natsorted

from cosh.misc import Printable


class DockerRepositoryRecord(Printable):

  def __init__(self, repository, namespace, name, tags=['latest']):
    self.tags = tags
    self.name = name
    self.repository = repository
    self.namespace = namespace
    self.image_name = ('%s/%s/%s' % (repository if repository else '', namespace, name)).lstrip('/')

  def __eq__(self, other):
    return isinstance(other, self.__class__) and ((self.name) == (other.name))

  def __ne__(self, other):
    return self.name != other.name

  def __lt__(self, other):
    return self.name < other.name

  def __le__(self, other):
    return self.name <= other.name

  def __gt__(self, other):
    return self.name > other.name

  def __ge__(self, other):
    return self.name >= other.name

  def __hash__(self):
    return hash(self.name)


class ComperableRepository:
  def __init__(self, namespace, name):
    self.name = name
    self.namespace = namespace

  def __eq__(self, other):
    return isinstance(other, self.__class__) \
           and ((self.name, self.namespace) == (other.name, other.namespace))

  def __ne__(self, other):
    return (self.name, self.namespace) != (other.name, other.namespace)

  def __lt__(self, other):
    return (self.name, self.namespace) < (other.name, other.namespace)

  def __le__(self, other):
    return (self.name, self.namespace) <= (other.name, other.namespace)

  def __gt__(self, other):
    return (self.name, self.namespace) > (other.name, other.namespace)

  def __ge__(self, other):
    return (self.name, self.namespace) >= (other.name, other.namespace)

  def __hash__(self):
    return hash((self.name, self.namespace))


class DockerRepositoryV1(Printable, ComperableRepository):
  DEFAULT_VALUE = 'registry.hub.docker.com'

  def __init__(self, namespace, name=DEFAULT_VALUE):
    super().__init__(name=name, namespace=namespace)

  def tags(self, image_name):
    r = requests.get('https://%s/v1/repositories/%s/%s/tags'
                     % (self.name, self.namespace.rstrip('/'), image_name)).json()
    return natsorted([tag['name'] for tag in r], reverse=True)

  # {
  #   "name": "actionspec/php70-fpm",
  #   "description": "php 7.0.30 FPM image for Magento 2.1.x and 2.2.x",
  #   "star_count": 0,
  #   "is_trusted": true,
  #   "is_automated": true,
  #   "is_official": false
  # }
  def list(self):
    r = requests.get('https://%s/v1/search?q=%s' % (self.name, self.namespace))
    search = r.json()
    search_results = search['results']
    while search['num_pages'] != search['page']:
      search = requests.get('https://%s/v1/search?q=%s&page=%d'
                            % (self.name, self.namespace, search['page'] + 1)).json()
      search_results += search['results']

    return [
      DockerRepositoryRecord(
          repository=None if self.name == DockerRepositoryV1.DEFAULT_VALUE else self.name,
          namespace=self.namespace,
          name=search_hit['name'].split('/')[1],
          tags=self.tags(search_hit['name'].split('/')[1]))
      for search_hit in search_results
      if search_hit['name'].startswith('%s/' % self.name.rstrip('/'))
    ]


class DockerStore(Printable, ComperableRepository):
  DEFAULT_NAME = 'store.docker.com'

  def __init__(self, namespace, name=DEFAULT_NAME):
    super().__init__(name=name, namespace=namespace)

  def __paged_results(self, url):
    r = requests.get(url)
    repos = r.json()
    results = repos['results']
    while repos['next']:
      r = requests.get(repos['next'])
      repos = r.json()
      results += repos['results']
    return results

  def tags(self, image_name):
    results = self.__paged_results('https://%s/v2/repositories/%s/%s/tags/?page_size=100'
                                   % (self.name, self.namespace.rstrip('/'), image_name))
    return natsorted([result['name'] for result in results], reverse=True)

  # {
  #   "user": "actions",
  #   "name": "vim",
  #   "namespace": "actions",
  #   "repository_type": "image",
  #   "status": 1,
  #   "description": "Docker actions: vim",
  #   "is_private": false,
  #   "is_automated": true,
  #   "can_edit": false,
  #   "star_count": 0,
  #   "pull_count": 2,
  #   "last_updated": "2018-08-15T00:40:22.330354Z"
  # }
  def list(self):
    results = self.__paged_results('https://%s/v2/repositories/%s?page_size=100'
                                   % (self.name, self.namespace))
    return [
      DockerRepositoryRecord(
          repository=None if self.name == DockerStore.DEFAULT_NAME else self.name,
          namespace=self.namespace,
          name=result['name'],
          tags=self.tags(result['name']))
      for result in results
    ]


class DockerRepositoryGcr:

  def __init__(self, namespace, name='registry.hub.docker.com', gcr_key_file=None):
    self.gcr_key_file = gcr_key_file
    self.name = name
    self.namespace = namespace
    self.__credentials = None

  def credentials(self):
    if not self.__credentials:
      warnings.filterwarnings("ignore",
                              "Your application has authenticated using end user credentials")
      if self.gcr_key_file:
        logging.debug('Using key file: %s' % self.gcr_key_file)
        self.__credentials = service_account.Credentials.from_service_account_file(
            self.gcr_key_file,
            scopes=['https://www.googleapis.com/auth/devstorage.read_write'])
      else:
        logging.debug('Using default credentials')
        self.__credentials, project = google.auth.default(
            scopes=['https://www.googleapis.com/auth/devstorage.read_write'])
    return self.__credentials

  def token(self):
    self.credentials().refresh(google.auth.transport.requests.Request())
    return self.credentials().token

  def tags(self, image_name, token=None):
    if not token:
      token = self.token()
    result = requests.get(
        'https://%s/v2/%s/%s/tags/list' % (self.name, self.namespace, image_name),
        headers={'Authorization': 'Bearer %s' % token}).json()
    return natsorted(result['tags'], reverse=True)

  def list(self):
    token = self.token()
    response = requests.get('https://%s/v2/%s/tags/list' % (self.name, self.namespace),
                            headers={'Authorization': 'Bearer %s' % token})
    return [
      DockerRepositoryRecord(repository=self.name,
                             namespace=self.namespace,
                             name=child,
                             tags=self.tags(child, token))
      for child in response.json()['child']
    ]

  def __repr__(self):
    return str(self.__class__) + ": " + str({'name': self.name, 'namespace': self.namespace})

  def __eq__(self, other):
    return isinstance(other, self.__class__) \
           and ((self.name, self.namespace, self.gcr_key_file)
                == (other.name, other.namespace, other.gcr_key_file))

  def __ne__(self, other):
    return ((self.name, self.namespace, self.gcr_key_file)
            != (other.name, other.namespace, other.gcr_key_file))

  def __lt__(self, other):
    return ((self.name, self.namespace, self.gcr_key_file)
            < (other.name, other.namespace, other.gcr_key_file))

  def __le__(self, other):
    return ((self.name, self.namespace, self.gcr_key_file)
            <= (other.name, other.namespace, other.gcr_key_file))

  def __gt__(self, other):
    return ((self.name, self.namespace, self.gcr_key_file)
            > (other.name, other.namespace, other.gcr_key_file))

  def __ge__(self, other):
    return ((self.name, self.namespace, self.gcr_key_file)
            >= (other.name, other.namespace, other.gcr_key_file))

  def __hash__(self):
    return hash((self.name, self.namespace, self.gcr_key_file))


class DockerRepositoryFactory(Printable):
  def __init__(self, repository, gcr_key_file=None):
    self.gcr_key_file = gcr_key_file
    self.repository = repository
    self.__versions = []

  def versions(self):
    if not self.__versions:
      repo_split = self.repository.split('/')
      # TODO: Use .match instead
      m = re.search('(?=^.{4,253}$)(^((?!-)[a-zA-Z0-9-]{1,63}(?<!-)\.)+[a-zA-Z]{2,63}$)',
                    repo_split[0])
      if m:
        if repo_split[0].endswith('gcr.io'):
          logging.debug('Adding gcr docker repository...')
          self.__versions += [
            DockerRepositoryGcr(name=repo_split[0],
                                namespace=repo_split[1],
                                gcr_key_file=self.gcr_key_file)]
        else:
          v1_response = requests.get('https://%s/v1' % self.repository)
          if v1_response.ok:
            logging.debug('Adding v1 docker repository...')
          self.__versions += [DockerRepositoryV1(name=repo_split[0], namespace=repo_split[1])]
        # v2_response = requests.get('https://%s/v2' % self.repository)
        # if v2_response.ok:
        # if v2_response.status_code == 401:

      else:
        logging.debug('Adding docker store repository...')
        self.__versions += [DockerStore(namespace=repo_split[0])]

    logging.debug('Docker factory returns: %s' % self.__versions)
    return self.__versions
