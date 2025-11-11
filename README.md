# Mamma Mia toolbox

## Description

###  Main function
This toolbox simulates the payload of a platform that is sampling the ocean. Input trajectories have a payload simulated 
that relates to the sensors on the platform. Optionally the toolbox can also simulate the trajectory of a platform, currently
only slocum gliders are supported, although autosubs, argo floats and airborne (sampling ocean surface) are expected to be added 
in future releases.

When give a trajectory (either simulated, from an actual AUV or csv waypoints), the toolbox will search and find the best models
to create a world that encompasses the trajectory. The world will hold as much data as can be found that matches the platforms
simulated payload.

Each trajectory is defined as a mission, these can be added to a campaign allowing multiple platforms to operate together,
these missions can be different platforms e.g. glider and an Autosub or the same platform with different configurations. 
e.g. same glider with different payloads or the same glider with the same payload but with different model sources set.

When the mission is flown, Mamma Mia will create a simulated data payload of what would be expected from the glider if it had
been operated in the real world with model data substituting observations. Some effect is made to match datasets that gliders
collect operationally, e.g. different sensor rates can be specified and comparable metadata is generated.

### Supplementary function
In addition to simulating a gliders data payload, Mamma mia can support the platform simulator by provided interpolated data
e.g. (velocity and density) to a specified spatial and temporal coordinate. This allows the simulator to take into account the 
environment when creating the trajectory.

### Example output

![example_trajectory](img/example_trajectory.png)
*Example trajectory of a glider, the colour denotes time (the darker the colour the older the section of the trajectory is)*

When processed through Mamma mia, this trajectory results in a payload, containing interpolated data from one or more models. 
The screenshots below shows an example mission of a slocum glider off Greenland

![example_reality](img/example_payload.png)
*Example glider temperature payload produced by Mamma mia, this has been generated using the trajectory above and a CMEMS global model.*

![example_reality](img/example_payload2.png)
*Example glider salinity payload produced by Mamma mia, this has been generated using the trajectory above and a CMEMS global model.*

## Requirements
Mamma mia has a number of dependencies, (numpy pyinterp, xarray, zarr, ploty etc). These can be installed using a conda
compatible package manager e.g. conda, miniconda, mamba, miniforge etc.

## Installation
Assuming a conda package manager as a virtual env:

```shell
$ conda create -n mm python=3.13 esmpy pyinterp  # these dependancies aren't easily installable via pip
```
This should create a virtual environment containing python 3.13 which Mamma mia is compatible with,

```shell
$ conda activate mm
```
Then you can install Mamma Mia itself, note the command below must be run in the top level of the Mamma Mia repository.
```shell
$ pip install .
```
### Optional dependancies
By default no simulator is installed alongside Mamma Mia, this is to simplify the install process as for example the glidersim
requires an C++ compiler to install all its dependencies, and this is an additional complication that may not be required e.g.
if the user doesn't want to simulate a glider. To install Mamma Mia with the glidersim:

```shell
$ pip install '.[glidersim]'
```
As other simulators become available they will be added here, e.g. parcels for argo float simulation.

To install all simulators (currently just glidersim) then:

```shell
$ pip install '.[all]'
```

### Example scripts
There are some example scripts showing how Mamma Mia can be used.

#### campaign_test.py
Running this script will run an example campaign with a single glider mission that undertakes a number of dives off
Greenland in 2019. It demonstrations the main functions of Mamma mia as follows:

- creating a campaign
- listing available platform types
- listing available platforms of a specific type (glider)
- creating a platform/entity from the inventory
- listing available CTD sensors for that platform entity
- listing available radiometers for that platform entity
- creating a CTD entity suitable for the platform
- updating the CTD sample rate
- registering the sensor to the platform
- creating a new entity of the same platform but with no CTD to add
- register both platforms to the campaign
- create custom metadata objects such as 
  - creator
  - publisher
  - contributor
- add a mission to the campaign, specifying which entity to use and where the trajectory is located
- initialising the catalog which is used to determine what model data is availble
- building the missions in the campaign (downloads model data, creates interpolators etc)
- runs the campaign which flies each mission (generates interpolated resampled data to match what is specified in the sensors)
- mission is visualised both as a trajectory and an interpolated payload
- campaign exported as a zarr group.

#### dvr_test.py
Running this script demonstrates how Mamma mia can be used to get interpolated environmental data to help simulate a platform
and generate a more accurate trajectory.

It demonstrates this as follows:

- creates an extent (Mamma mia uses trajectory to determine this in main operation)
- creates a point (where interpolated data is desired)
- Creates a reality (contains model data and interpolators as required for the extent specifed)
- shows how to teleport (returns interpolated velocities and temp/salinity for the provided point)

## Usage
Mamma Mia is designed to be flexible and be able to used as a python module allowing an interface such as a REST API, 
GUI or just a python script to be overlaid on top. An integrated product containing:

- platform simulator
- mamma mia toolbox
- user interface 

may be created in the future.

## Architecture
Mamma mia is structured in the following way with the following concepts:

- parameters (this is specific variable such as temperature)
- sensors (this is a specific sensor such as a CTD that measures , temperature, salinity, pressure)
- platforms (this is a specific platform such as a slocum glider)

Each of the components above are specified in separate JSON files, mamma mia reads these on import and creates an immutable
inventory for each. Users can then create entities from this inventory that are mutable.

It is not currently possible to add new platforms, sensors and parameters, but a future release will add the ability for local 
JSON or similar files to be used.

### Vocabulary
Mamma mia uses the following terms to describe different aspects of the toolbox

- World (subset of a model the encompasses a trajectory)
- Trajectory(flight through 3D space and time)
- Payload (interpolated model data onto resampled flight to match sensor sampling rate)
- Mission (all the above stored in one object)
- Campaign (holds missions, platforms, interpolators in one group that can be exported)

### Parameters
These specify a specific variable, an example being in-situ temperature:

```json
            {
                "parameter_id": "INSITU_TEMPERATURE",
                "identifier": "SDN:OG1::TEMP",
                "vocab_url": "https://vocab.nerc.ac.uk/collection/OG1/current/TEMP/",
                "standard_name": "Sea temperature in-situ ITS-90 scale",
                "unit_of_measure": "Degrees Celsius",
                "unit_identifier": "SDN:P06::UPAA",
                "parameter_definition": "Temperature of the water body by CTD or STD",
                "alternate_sources": ["POTENTIAL_TEMPERATURE","CONSERVATIVE_TEMPERATURE"],
                "alternate_labels": ["TEMPERATURE"],
                "source_names": ["sci_water_temp"]
            }
```
Most fields cover the vocabulary and specific details of the parameter, source_names field lists input variable aliases,
from model source etc. alternate_sources details what other parameters can be used as a source, e.g. POTENTIAL_TEMPERATURE or
CONSERVATIVE_TEMPERATURE can be converted into INSITU_TEMPERATURE.

### Sensors
These specify a specific set of parameters along with a sampling rate. They can mirror a real sensor, the following is 
an CTD that is compatible with a slocum glider model G2

```json
            {
                "sensor_model": "Slocum Glider G2 CTD",
                "instrument_type": "CTD",
                "specification": {
                    "INSITU_TEMPERATURE": {
                        "accuracy": 0.001,
                        "resolution": 0.001,
                        "drift_per_month": 0.0002,
                        "range": [-5, 42],
                        "percent_errors": false,
                        "noise_std": 0.0005,
                        "meta_data": "insitu temperature"
                    },
                    "PRACTICAL_SALINITY": {
                        "accuracy": 0.005,
                        "resolution": 0.0001,
                        "drift_per_month": 0.003,
                        "range": [0, 42],
                        "percent_errors": false,
                        "noise_std": 0.0025,
                        "meta_data": "practical salinity"
                    },
                    "PRESSURE": {
                        "accuracy": 0.1,
                        "resolution": 0.002,
                        "drift_per_month": 0.0042,
                        "range": [0, 2000],
                        "percent_errors": true,
                        "noise_std": 0.0005,
                        "meta_data": "pressure"
                    }
                },
                "platform_compatibility": ["Slocum_G2"]
            }
```

### Platforms
This determines what platforms are available within Mamma Mia, currently Slocum G2 and ALR 1500 are specified.

```json
{
    "platforms": {
        "glider": [
            {
                "platform_type": "Slocum_G2",
                "platform_manufacturer": "Teledyne Webb Research",
                "NEMA_coordinate_conversion": true
            }
        ],
        "alr": [
            {
                "platform_type": "ALR_1500",
                "platform_manufacturer": "National Oceanography Centre",
                "NEMA_coordinate_conversion": false
            }
        ]
    }
}
```


### World
The world is the model data that will be interpolated onto the glider's trajectory. This is currently downloaded from 
NOC data sources or CMEMS for the full extent of the trajectory

### Trajectory
The trajectory consists of a zarr group containing the latitudes, longitudes, depths as well as datetimes.

### Payload
Payload is a zarr Group that holds arrays that reflect the specified sensors in the virtual AUV, this is populated with 
interpolated data from the world.

### Mission
This is the parent/main class for Mamma mia in that it holds all the other classes and performs the main functions.

### Campaign
This is the class a MM user is expected to interact with, it holds all the missions, interpolators and auv's required for a 
deployment or campaign.

## Using the glider simulator
The simulator has been modified so it works with the example script in its README. A new mission profile has been created
called mm1, this will run a glider simulation that results in the trajectory above. (6 hours no surfacing a single waypoint)

To generate the simulation output, there needs to be a bathymetry file. GEBCO is suitable and compatible with the mm1 
configuration. However, the bathymetry needs to be a subset from the global dataset. Easiest method is to download the subset
from BODC. Downloading 45-48 N and -6.5 to -8 E should be sufficient.

Generate the output by running the example.py script:

```shell
$ python example.py
```

The output "comet-mm1.nc" can then be copied into the MammaMia repository, where it should be recognised by the campaign_test.py script.

## Reality
Mamma Mia also has the abilty to return interpolated data at requested points, this is to provide environment data for the
glider simulator as part of the trajectory creation. See dvr_test.py for an example implementation.

## Known issues

When updating to python 3.12, dbdreader (glider sim dependancy) caused some issues with a missing arch (it had x84 but not arm64) so was crashing on import
This shouldn't really happen but dbdreader's setup.py seems to be written to cover linux and windows but not macos, I managed to resolve by running the following:
```shell
$ arch -arm64 pip install dbdreader --no-cache --force-reinstall
```
This explicitly installs the arm64 arch version bypassing any cached and installed versions. This is only likely to be an issue
for M series Macbooks.



