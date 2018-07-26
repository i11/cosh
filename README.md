# cosh

Container shell is meant to act as an aggregator or a manager for containers that were built
following the Unix philosophy (i.e. minimalistic and self-contained).
It provides the means to dynamically assemble required runtime environment.

Imagine the scenario where certain project would require a number of commands for it to run
or build that would not be directly present on the given system.
In such case cosh would attempt to acquire corresponding images and execute commands
through running the containers as if it would be the usual command execution. 