import s3fs
import xarray as xr
import intake
import matplotlib.pyplot as plt
import json

from pystac import Catalog, Item, Asset, MediaType,CatalogType
import os

from datetime import datetime, timezone
from shapely.geometry import Polygon, mapping

#s3 = s3fs.S3FileSystem(endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk",anon=True)
#s3_store = s3fs.S3Map('s3://mamma-mia/eORCA12_201908',s3=s3)

cat = intake.open_catalog('src/mission/catalog.yml')
data = cat.eORCA12_201908.to_dask()
print(data)

cropped_data = data.sel(y=slice(2500,3000), x=slice(3250,3750),deptht=slice(5,200))

#data = xr.open_zarr(s3_store)
#
print(cropped_data)
temp = cropped_data.thetao
temp = temp.sel(deptht=5,method='nearest')
temp.plot()
print(temp)
print("the end")

plt.show()
# catalog = Catalog(id='mamma-mia-catalog',
#                          description='This catalog is a basic demonstration catalog Using the Jasmin Object Store.')
#
# bbox = [-180, -90, 180, 90]
# footprint = Polygon([
#     [-180, -90],
#     [-180, 90],
#     [180, 90],
#     [180, -90]
# ])
#
# datetime_utc = datetime(year=2019,month=8,day=1,hour=0,minute=0,second=0,microsecond=0)
#
# item = Item(id='eORCA12',
#                  geometry=mapping(footprint),
#                  bbox=bbox,
#                  datetime=datetime_utc,
#                  properties={})
#
# catalog.add_item(item)
# item.add_asset(key='zarr',
#                asset=Asset(href='https://noc-msm-o.s3-ext.jc.rl.ac.uks3://mamma-mia/eORCA12_201908',
#                            media_type=MediaType.ZARR))
#
# catalog.describe()
# catalog.normalize_hrefs(os.path.join(os.getcwd(), "stac"))
# catalog.save(catalog_type=CatalogType.ABSOLUTE_PUBLISHED)
