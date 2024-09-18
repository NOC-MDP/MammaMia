import pystac
from datetime import datetime
import xarray as xr

# Open the static STAC catalog (e.g., hosted on S3)
catalog_url = "catalog.json"
catalog = pystac.Catalog.from_file(catalog_url)

# Define the time range you're interested in (e.g., 2019)
start_time = datetime(2019, 1, 1,0,0,0)
end_time = datetime(2019, 12, 31,23,59,59)

# Traverse through the catalog to find matching items
for item in catalog.get_all_items():
    start_datetime_str = item.properties.get("start_datetime")
    end_datetime_str = item.properties.get("end_datetime")

    if start_datetime_str and end_datetime_str:
        # Convert strings to datetime objects for comparison
        start_datetime = datetime.strptime(start_datetime_str,"%Y-%m-%dT%H:%M:%SZ")
        end_datetime = datetime.strptime(end_datetime_str,  "%Y-%m-%dT%H:%M:%SZ")

        # Check if the item is within the desired date range
        if start_time <= start_datetime <= end_time and start_time <= end_datetime <= end_time:
            # Also check if the variable is temperature
            if item.properties.get("model:variable") == "temperature":
                print(f"ID: {item.id}")
                print(f"Start Datetime: {item.properties['start_datetime']}")
                print(f"End Datetime: {item.properties['end_datetime']}")
                print(f"Temperature Zarr URL: {item.assets['data'].href}")
                print(f"Bounding box: {item.bbox}")
                print(f"Properties: {item.properties}")
                print("\n")
                ds = xr.open_zarr(item.assets['data'].href, chunks='auto')

                # Print out some information about the dataset
                print(ds)

                # Perform operations on the dataset (lazy loading with Dask)
                # Example: Access the temperature variable
                temperature = ds['thetao']
                print(temperature)


