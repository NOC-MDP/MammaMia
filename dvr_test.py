from mamma_mia import Extent, Point, RealityWorld, sensor_inventory

print("<=========> starting Mamma Mia Velocity Reality test run <===========>")

ctd = sensor_inventory.create_entity(entity_name="ctd",sensor_type="CTD",sensor_ref="mamma_mia")
adcp = sensor_inventory.create_entity(entity_name="adcp",sensor_type="ADCP", sensor_ref="mamma_mia")
extent = Extent(max_lat=58.0,
                min_lat=56.0,
                min_lng=6.0,
                max_lng=7.0,
                max_depth=200,
                start_dt="2023-01-01T00:00:00",
                end_dt="2023-01-07T00:00:00"
                )
point = Point(latitude=57.1,
              longitude=6.4,
              depth=12.0,
              dt="2023-01-03T00:00:00",

)

DVR = RealityWorld(extent=extent,adcp=adcp,ctd=ctd)
print("the end")
# Real = DVR.teleport(point=point)
# print(Real)
# print(">===========< Mamma Mia Velocity Reality test complete >==========<")