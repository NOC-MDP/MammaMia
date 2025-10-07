from OceanDataStore import OceanDataCatalog
import matplotlib.pyplot as plt

catalog = OceanDataCatalog(catalog_name="noc-model-stac")

catalog.search(collection='noc-npd-era5', standard_name='sea_surface_temperature')

print(catalog.Items[0])

ds = catalog.open_dataset(id=catalog.Items[0].id,
                          start_datetime='1980-01',
                          end_datetime='1990-12',
                          )

print(ds)

ds['tos_con'].mean(dim='time_counter').plot(cmap='RdBu_r')

plt.show()