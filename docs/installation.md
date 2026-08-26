---
icon: lucide/cog
title: "Installation"
---

The following steps will enable you to install MAMMA MIA on your local system. It is expected the user is familiar with git, conda and python in general.

## Clone the repository

First clone a MAMMA MIA release, it is highly recommended to download the latest one which can be found on the releases page.

``` bash
$ git clone https://github.com/NOC-MDP/MammaMia/releases/tag/0.4.1
```

The above command will clone the 0.4.1 release of MAMMA MIA.

## Set up python environment

Assuming a conda package manager as a virtual env:

``` bash
$ conda create -n mm python=3.13 esmpy pyinterp  # these dependancies aren't easily installable via pip
```

This should create a virtual environment containing python 3.13 which MAMMA MIA is compatible with,

``` bash
$ conda activate mm
```

Then you can install MAMMA MIA itself, note the command below must be run in the top level of the MAMMA MIA repository.

``` bash
$ pip install .
```

## Optional dependencies

By default no simulator is installed alongside MAMMA MIA, this is to simplify the install process as for example the glidersim dependency requires an C++ compiler to be able to install all of its dependencies, and this is an additional complication that may not be required e.g. if the user doesn't want to simulate a glider. To install MAMMA MIA with the glidersim:

``` bash
$ pip install '.[glidersim]'
```

**NOTE** You will need an C++ compiler available on the command line where you are installing MAMMA MIA to be able to install glidersim.

As other simulators become available they will be added here, e.g. parcels for argo float simulation.

To install all simulators (currently just glidersim) then:

``` bash
$ pip install '.[all]'
```

## Windows Support

The above steps will most likely not work on windows due to dependencies not having pre built binaries available for Windows (e.g. PyInterp, esmpy). While this is surmountable, by building these dependencies, the recommended workaround is to use a docker or similar container containing a linux distribution or Windows Subsystem for Linux.
