import docker


class DockerRequirement:
  def __init__(self):
    self.client = docker.from_env()

  def check(self):
    client = docker.from_env()
    client.ping()
