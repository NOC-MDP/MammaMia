import intake
from datetime import datetime,timezone
import matplotlib.pyplot as plt

# Load the catalog
catalog = intake.open_catalog('catalog.yml')

# Define your search criteria
search_bbox = [-50, -30, 50, 30]  # A region with longitude/latitude bounds
search_start_time = datetime(2019, 1, 1,tzinfo=timezone.utc)
search_end_time = datetime(2019, 1, 30,tzinfo=timezone.utc)
search_terms = ["temperature","salinity"]
for term in search_terms:
    # Search through the catalog based on spatial and temporal extent
    search_results = []
    for entry_name, entry in catalog.items():
        metadata = entry.describe()['metadata']

        # Get the spatial and temporal extents from metadata
        spatial_extent = metadata.get('spatial_extent', [])
        temporal_extent = metadata.get('temporal_extent', [])
        aliases = metadata.get('aliases', [])

        # Convert temporal extent strings to datetime objects for comparison
        if temporal_extent:
            start_datetime = datetime.fromisoformat(temporal_extent[0].replace("Z", "+00:00"))
            end_datetime = datetime.fromisoformat(temporal_extent[1].replace("Z", "+00:00"))

            # Check if the item is within the desired date range and spatial bounds
            if (spatial_extent and
                    search_bbox[0] >= spatial_extent[0] and search_bbox[2] <= spatial_extent[2] and
                    search_bbox[1] >= spatial_extent[1] and search_bbox[3] <= spatial_extent[3] and
                    search_start_time >= start_datetime and search_end_time <= end_datetime and
                    term in aliases):
                search_results.append(entry)

    # Print the search results
    if search_results:
        print("Found datasets:")
        for result in search_results:
            print(f"- {result.name}")
            data = result.to_dask()
            var = result.describe()['metadata']["variable"]
            print(data)
    else:
        print("No datasets found with the specified spatial/temporal criteria.")


    cropped_data = data.sel(y=slice(2500,3000), x=slice(3250,3750),deptht=slice(5,200),time_counter="2019-01-16")
    print(cropped_data)
    var_data = cropped_data[var]
    var_subset = var_data.sel(deptht=5,method='nearest')
    var_subset.plot()
    print(var_subset)
    plt.show()
print("the end")



