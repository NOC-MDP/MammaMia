---
icon: lucide/file-code
title: "Specifications"
---

# Specifications

## Specification file format
MAMMA MIA uses a toml format specification file to configure it, this is where users will specify platforms and sensors and set what model source to use when simulating payloads. Examples are provided in the examples/spec_files folder in the repository.

The specification file is split into the following sections:

- platform
- trajectory
- navigation
- sensors

There are various key/values that need to be present, the following sections detail what is required to be a compatiable specification file.

### Platform specification
This section determines platform specific behaviour, for example

```toml
[specification.platform]
type = "glider"
NMEA_coordinates = true
ascent_thresh = 0.05  # m/s
descent_thresh= -0.05  # m/s
near_surface_thresh = 1
```

**Type**, the user must specify "type", this is a string that is stored as metadata, showing what platform the input trajectory represents.

**NMEA_coordinates** used by some platforms (gliders) in place of latitude and longitude, depending on the input trajectory (e.g. if it has come from a simulator or unprocessed real glider) then the coordinates will need converting into latitude and longitude. Processed glider files will generally have been converted so this will need to be set to false in that case.

**ascent_thres/decent_thres** this is the threshold used to determine if the platform trajectory is descending or climbing. MAMMA MIA determines the behaviour of a platform into four different states:

- diving (decent_thres exceeded)
- climbing (ascent_thres exceeded)
- surfaced (neither decent and ascent exceeded AND near_surface_thres is not exceeded)
- floating (decent/acent thres is not exceeded BUT near_surface_thres is)

These behaviours allow the output data to be easily split into dives.

**near_surface_thres** is used to set if a platform is "surfaced".

### Trajectory specification

```toml
[specification.trajectory]
path = "../data/RAPID-mooring/rapid-mooring.nc"
```

This sets the path to the input trajectory file that MAMMA MIA will use, this can be generated from an inbuilt simulator, e.g. glidersim for slocum gliders or parcels for ARGO floats (**NOTE** PARCELS is not yet integrated due to not supporting Zarr version 3 this is expected to be available in PARCELS version 4 when released). Real glider files output files can be used e.g. from [BODC Deployment catalogue](https://platforms.bodc.ac.uk/deployment-catalogue/) . The last option is way points listed in a CSV file, e.g. an ocean transect. Care will need to be take to ensure the spatialtemporal points are realistic for the platform.

### Navigation specification

```toml
[specification.navigation]
latitude = "m_lat"
longitude = "m_lon"
depth = "m_depth"
pitch = "m_pitch"
time = "time"
```

This section details the variable names for each of the navigation variables, e.g. latitude, longitude, depth etc. Depending on trajectory input/simulator these can vary.

### Sensor specification

This section specifies the sensors and allows custom ones to be created, each sensor has its own section defined as "specification.sensors.sensor_name.variable_name". An CTD temperature sensor is documented below that is "measuring" conservative temperature. Each sensor that is desired to be added to the platform requires a specification like this.

```toml
[specification.sensors.ctd.conservative_temperature]
# source_id = "noc-npd-era5/npd-eorca12-era5v1/gn/T1m_4d"
source_id = "../rapid_data/2_RAPID36_1d_gridT_RAPID1_202303-202303.nc"
variable_name = "toce_con"
accuracy = 0.001
resolution = 0.0001
drift_per_month = 0.0002
range = [-5, 42]
percent_errors = false
noise_std = 0.0005
```

The specification covers the model source, the variable name and then the observation errors parameters. 


!!! note "Data Constraints"

    Every sensor entry can have a different source, MAMMA MIA will download and cache all the required data. This may be quite large if the trajectory covers a large area over a long time and the user requests a high temporal and spatial resolution source.

#### Source id
This is a string that tells MAMMAMIA where to get the model data from, this can currently be one of three sources, CMEMS, OceanDataStores (NOC) and local paths. If the string starts with "noc" MAMMAMIA will use OceanDataStore to download the model, if it starts with "cmems" then it will use copernicusmarinetool box to download and if it is anything it, a path is assumed and MAMMAMIA will try to open the file using xarray. The above example is using a local file, but there is also a commented out OceanDataStore id.

To find suitable model ids, OceanDataStore has a catalog [here](https://noc-msm.github.io/OceanDataStore/catalog/) each entry has an accompanying catalog.open_dataset() example in it. This will provide the model_id. e.g.

```python
 catalog.open_dataset(id='noc-npd-jra55/npd-eorca025-jra55v1/r1i1c1f1/T1y_3d')
```

And CMEMS has a portal [here](https://data.marine.copernicus.eu/products) an example id being "cmems_mod_glo_phy_anfc_0.083deg_P1M-m" these are located in the data access tab for each product under each dataset type. 

#### Variable Name
Name of the variable, this must match the model source and can be verified using same links above for model id.

#### Synthetic Observations
MAMMA MIA can also converting the model data into synthetic observations, it does this by applying realistic noise and errors that are specified in the rest of the sensor specification.

##### Error/Noise parameters
Users should use values that are appropriate to the sensor they are trying to emulate, the specification of the real sensor can be used to set the following

- accuracy
- resolution
- drift per month
- range

If the sensor specification is in percentage terms rather than absolute values then set the percent_errors option to True. Finally the standard deviation of the noise of the sensor can be set here. The higher the value the more noise that is applied to the timeseries. This can emulate sensors with higher or lower signal to noise ratios.
