from OceanDataStore import OceanDataCatalog
from mamma_mia import WorldExtent
from datetime import datetime
import matplotlib.pyplot as plt



catalog = OceanDataCatalog(catalog_name="noc-model-stac")
parameters = ["thetao_con"]
catalog.search(collection="noc-npd-era5",variable_name=parameters[0])

world_extent = WorldExtent(lon_max=-50.0,
                           lon_min=-60.0,
                           lat_max=40.0,
                           lat_min=0.0,
                           depth_max=1000.0,
                           time_end="2023-12-31T23:59:59",
                           time_start="2023-12-31T23:59:59")
world_start = datetime.strptime(world_extent.time_start,"%Y-%m-%dT%H:%M:%S")
world_end = datetime.strptime(world_extent.time_end,"%Y-%m-%dT%H:%M:%S")
match = 0
matched_items = []
for item in catalog.Items:
    if (
    item.bbox[0] <= world_extent.lon_min and
    item.bbox[2] >= world_extent.lon_max and
    item.bbox[1] <= world_extent.lat_min and
    item.bbox[3] >= world_extent.lat_max and
    datetime.strptime(item.properties["start_datetime"],"%Y-%m-%dT%H:%M:%SZ") < world_start and
    datetime.strptime(item.properties["end_datetime"],"%Y-%m-%dT%H:%M:%SZ") > world_end
    ):
        for parameter in parameters:
            if parameter in item.properties["variables"]:

                print(f"found a match for {parameter} item id: {item.id}")
                matched_items.append(item)

print(f"{matched_items.__len__()} matches found")


ds = catalog.open_dataset(id="noc-npd-era5/npd-eorca025-era5v1/gn/T5d_4d",
                          start_datetime='2023-01',
                          end_datetime='2023-02',
                          bbox=(world_extent.lon_min,world_extent.lat_min,world_extent.lon_max,world_extent.lat_max),
                          )

print(ds)
ds.to_zarr(store="noc-npd-era5",mode="w")

# ds['thetao_con'].mean(dim='time_counter').plot(cmap='RdBu_r')
#
# plt.show()