# Mamma Mia toolbox

## Description
This toolbox enables the simulation of a glider through a models "virtual reality". A user provides a set of way points and can easily 
generate a suitable sawtooth trajectory for the glider from these points. A world is created which the glider will fly through, this 
comprises a suitable model or set of models. When creating the virtual glider the user can define a sensor suite which can comprise of 
different instrumentation, e,g, CTD or ADCP. All together these components are defined in a mission, that when executed will return a 
"reality" that contains the interpolated values that the virtual glider observes during its mission. 

![way_points](img/example_waypoints.png "Waypoints")
*Example waypoints that could be provided to Mamma mia as a multipoint geoJSON*

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
Mamma mia uses pytest to test its code, to test for correction installation please run:

```shell
$ pytest test.py
```
This will execute the test suite and display the results. All tests should pass.

## Usage
Mamma mia has the following concepts:

- AUV (virtual glider)
- Sensors (virtual sensors defined in suites and groups)
- World (subset of a model)
- Trajectory (glider path through 3D space and time)
- Reality (interpolated model data onto glider trajectory)
- Mission (all the above stored in one object)

### AUV (virtual glider)
This is represented in Mamma mia as a class object with fields holding parameters required for glider simulation e.g.

* speed
* dive rate
* dive angle
* surface rate
* surface angle

It also holds parameters about the dive, e.g.

* time at surface
* time at depth
* target depth
* min depth etc.

## Outstanding development
