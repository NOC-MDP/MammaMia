from mamma_mia import Campaign
from mamma_mia import inventory

campaign = Campaign(name="ALR arctic visualisation",
                    description="single ALR capability demo in the arctic",
                    verbose=True
                    )

ALR4 = inventory.create_platform_entity(entity_name="ALR4",
                                        platform="ALR_1500",
                                        serial_number="ALR_4")

ALR4.register_sensor(sensor_type="CTD")

campaign.register_platform(entity=ALR4)

# # add ALR4 mission
campaign.add_mission(mission_name="Arctic Visualisation",
                     title="Under Ice capability demo",
                     summary="",
                     platform_name="ALR4",
                     trajectory_path="arctic_vis_traj.csv",
                     source_location="CMEMS",
                     mission_time_step=60)

# build missions (search datasets, download datasets, build interpolators etc)
campaign.build_missions()

# run/fly missions
campaign.run()
campaign.missions["Arctic Visualisation"].plot_trajectory()
campaign.missions["Arctic Visualisation"].show_payload()
campaign.export()

import zarr
import pandas as pd

# Open the Zarr group
zg = zarr.open_group("/Users/thopri/MammaMia/ALR_arctic_visualisation.zarr/Arctic Visualisation/payload", mode="r")

# Collect all 1D arrays into a DataFrame
data = {name: zg[name][:] for name in zg.array_keys()}

df = pd.DataFrame(data)

# Save to CSV
df.to_csv("output.csv", index=False)
