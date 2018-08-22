# cosh

Container shell is meant to act as an aggregator or a manager for containers that were built
following the Unix philosophy (i.e. minimalistic and self-contained).
It provides the means to dynamically assemble required runtime environment.

Imagine the scenario where certain project would require a number of commands for it to run
or build that would not be directly present on the given system.
In such case cosh would attempt to acquire corresponding images and execute commands
through running the containers as if it would be the usual command execution. 

## Local experimentation
```sh
pip install -r requirements.txt
cosh --help
```

## Examples

```bash
cosh git status
```

```bash
cosh java -version
```

```bash
cosh java:8-jdk-latest -version
```

```bash
cosh gcloud config list
```

```bash
# Interactive
cosh sbt
```

## Advanced examples

### Use cosh to do a maven build
```bash
# Cloning repo
cosh git clone https://github.com/i11/jackson-datatype-datastore
cd jackson-datatype-datastore

# Compiling and running tests. Specific version is required since project depends on java8
cosh mvn:3.5.4-java8-2 clean test
```

### Use cosh for gcloud as docker's credential helper
```bash
# Configure docker's gcloud credential helper
cosh gcloud auth configure-docker

# Docker insists on matching executable in the PATH
echo -e '#!/bin/bash -e'"\ncosh docker-credential-gcloud \"\$@\"" > /usr/local/bin/docker-credential-gcloud
chmod +x /usr/loca/bin/docker-credential-gcloud

# Get your image
docker pull gcr.io/your-project/your-image-name:tag
```

See https://store.docker.com/profiles/actions for more available commands.

## Limitations

* The project is at very very very early stage. It is profoundly raw and has a lot of quirks at this point in time.

## Contribution

Please let me know what do you think and how it could becime more helpful for you. Thanks!
