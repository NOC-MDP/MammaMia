---
icon: lucide/rocket
title: "MAMMA MIA Documentation"
---

## Summary

MAMMA MIA is a platform payload simulator

This toolbox simulates the payload of a platform that is sampling the ocean. Input trajectories have a payload simulated that relates to the sensors on the platform. Optionally the toolbox can also simulate the trajectory of a platform, currently only slocum gliders are supported, although autosubs, argo floats and airborne (observing ocean surface) are expected to be added in future releases.

When give a trajectory (either simulated, from an actual AUV or csv waypoints), the toolbox will search and find the best models to create a world that encompasses the trajectory. The world will hold as much data as can be found that matches the platforms simulated payload.

Each trajectory is defined as a mission, these can be added to a campaign allowing multiple platforms to operate together,these missions can be different platforms e.g. glider and an Autosub or the same platform with different configurations.e.g. same glider with different payloads or the same glider with the same payload but with different model sources set.


When the mission is flown, Mamma Mia will create a simulated data payload of what would be expected from the glider if it had been operated in the real world with model data substituting observations. Some effect is made to match datasets that gliders collect operationally, e.g. different sensor rates can be specified and comparable metadata is generated.
=======
When the mission is flown, Mamma Mia will create a simulated data payload of what would be expected from the glider if it had been operated in the real world with model data being used to simulate observations. Some effect is made to match datasets that gliders collect operationally, e.g. different sensor rates can be specified and comparable metadata is generated.


MAMMA MIA supports the following inputs:

-   NetCDF/Zarr trajectories

-   waypoints from CSV

MAMMA MIA also simulates the following platforms:

-   slocum gliders, providing environmental data during simulation.

Future simulator integration's planned:

-   Autosub (using Autonomy Sim)

-   ARGO floats/drifters (using Parcels)

## Example output

The following image show example payloads that have been simulated by MAMMA MIA.

![In-situ temperature parameter of simulated payload from a Slocum Glider](images/Picture%201.png){fig-align="center"}

![Practical Salinity payload from a virtual glider performing an “virtual mooring mission”](images/Picture%202.png){fig-align="center"}

![ALR simulating BIOCARBON Iceland to Scotland mission showing in-situ temperature.](images/Picture%203.png){fig-align="center"}

![ALR simulated payload of dissolved oxygen](images/Picture%204.png){fig-align="center"}
