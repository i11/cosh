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

```sh
cosh git status
```

```sh
cosh java -- -version
```

```sh
cosh java:8-jdk-latest -- -version
```

## Limitations

The project is at very very very early stage. It is profoundly raw and has a lot of quirks at this point in time.

## Contribution

Please let me know what do you think and how it could becime more helpful for you. Thanks!
