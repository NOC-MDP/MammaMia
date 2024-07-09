# Mamma Mia toolbox

## Description
This toolbox enables the simulation of a glider through a models "virtual reality". A user provides a set of way points and can easily 
generate a suitable sawtooth trajectory for the glider from these points. A world is created which the glider will fly through, this 
comprises a suitable model or set of models. When creating the virtual glider the user can define a sensor suite which can comprise of 
different instrumentation, e,g, CTD or ADCP. All together these components are defined in a mission, that when executed will return a 
"reality" that contains the interpolated values that the virtual glider observes during its mission. 

## Requirements
Mamma mia has a number of dependencies, (numpy pyinterp, xarray zarr etc). These can be installed using a conda compatible package manager
e.g. conda, miniconda, mamba, miniforge etc.

## Installation
Assuming a conda package manager:

```shell
$ conda env create --file enviroment.yml
```
This should create a virtual environment containing all of Mamma mias dependencies. Ensure the environment is activated before using,

```shell
$ conda activate mm
```

## Testing

## Usage

## Outstanding development