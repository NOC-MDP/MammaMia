from mamma_mia import Extent, Point, RealityWorld

print("<=========> starting Mamma Mia Velocity Reality test run <===========>")


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

DVR = RealityWorld(extent=extent)
print("the end")
# Real = DVR.teleport(point=point)
# print(Real)
# print(">===========< Mamma Mia Velocity Reality test complete >==========<")