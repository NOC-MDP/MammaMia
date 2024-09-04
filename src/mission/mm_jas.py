import s3fs
import xarray as xr


s3 = s3fs.S3FileSystem(endpoint_url="https://noc-msm-o.s3-ext.jc.rl.ac.uk",anon=True)
s3_store = s3fs.S3Map('s3://mamma-mia/eORCA12_201908',s3=s3)

#cat = intake.open_catalog('src/mission/catalog.yml')
#data = cat.eORCA12_201908.to_dask()
data = xr.open_zarr(s3_store)

print(data)
print("the end")

