import docker

from cosh.misc import Printable


class DockerRequirement(Printable):
  def __init__(self):
    self.client = docker.from_env()

  def check(self):
    client = docker.from_env()
    client.ping()
