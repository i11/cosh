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
cosh java -- -version
```

```bash
cosh java:8-jdk-latest -- -version
```

```bash
# Interactive
cosh gcloud config list
```

```bash
# Interactive
cosh sbt
```

## Advanced examples

```bash
# Cloning repo
cosh git clone https://github.com/i11/jackson-datatype-datastore
cd jackson-datatype-datastore

# Compiling and running tests. Specific version is required since project depends on java8
cosh mvn:3.5.4-java8-1 clean test
```

## Limitations

The project is at very very very early stage. It is profoundly raw and has a lot of quirks at this point in time.

## Contribution

Please let me know what do you think and how it could becime more helpful for you. Thanks!
