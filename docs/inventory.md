---
layout: default
title: Inventory
nav_exclude: false
nav_order: 3
---
# Inventory
Mamma Mia uses an inventory system to store information about platforms, sensors and parameters.

## Parameters
Every parameter that is associated with a sensor needs to have an entry in the parameter inventory. This is loaded at
runtime from a set of json files. An example is shown here:

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
This shows the entry for insitu temperature, every parameter needs to have each of the above fields specified. Some are
purely meta data and not currently used by Mamma Mia e.g. unit_identifier or vocab_url. But some are critical for MammaMia to work
correctly. 

### Parameter Id
This is what Mamma Mia uses internally to reference the parameters, The standard format is capital letters seperated by an
underscore, although any string should work. 

### identifier
This is the vocab identifier for the specific parameter, it is specified within the vocabulary entry. This is for meta
data purposes only.

### vocab url
Denotes the location of the vobabulary used to define this parameter. The NERC vocab collection is generally used.

### standard name
Standard name of the variable, usually defined in the vocab but can be any string. 

### unit of measure
As defined in the vocab, can be any string and not used by Mamma Mia

### paramter definition
As defined in the vocab, can be any string and is not currently used by Mamma Mia

### alternative sources
A list of alternative parameters that be converted into this parameter, examples being conservative and potential
temperature being able to be converted into insitu temperature. **NOTE:** This will often require other data parameters
e.g. temperature conversions will require pressure, salinity etc. The conversion must also be supported by Mamma Mia.

### alternative labels
and alternative label for the parameter.

### source names
A list of names that a given parameter can be in model data files. E.g. thetao for pontential temperature, so_abs for
absolute salinity. This is one of the most important fields as if its incorrect MammaMia will not find any model data
for the parameter. And equally if it references a different parameter MammaMia will also not be aware and assume it is
parameter as defined in the JSON entry.

## Sensors
These hold the parameters for a given sensor type, e.g. CTD. They are also stored as an JSON file that is loaded at runtime.

```json
    {
        "sensor_model": "Generic CTD",
        "instrument_type": "CTD",
        "specification": {
            "POTENTIAL_TEMPERATURE": {
                "accuracy": -999.999,
                "resolution": -999.999,
                "drift_per_month": -999.999,
                "range": [-999.999, -999.999],
                "percent_errors": false,
                "noise_std": -999.999,
                "meta_data": "potential temperature"
            },
            "PRACTICAL_SALINITY": {
                "accuracy": -999.999,
                "resolution": -999.999,
                "drift_per_month": -999.999,
                "range": [-999.999, -999.999],
                "percent_errors": false,
                "noise_std": -999.999,
                "meta_data": "practical salinity"
            }
        },
        "platform_compatibility": ["mm"]
    }
```
The JSON entry above defines a generic CTD that is recording potential temperature and practical salinity, this is not a
realistic payload in reality but this CTD is used within MammaMia to provide density information to a simulator integration







