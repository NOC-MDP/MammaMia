from mamma_mia import Extent,Point,VelocityReality

print("<=========> starting Mamma Mia Velocity Reality test run <===========>")

extent = Extent(max_lat=58.0,
                min_lat=56.0,
                min_lng=6.0,
                max_lng=7.0,
                max_depth=200,
                start_dt="2019-01-01T00:00:00",
                end_dt="2019-01-07T00:00:00"
                )
point = Point(latitude=57.1,
              longitude=6.4,
              depth=12.0,
              dt="2019-01-03T00:00:00",

)
VR = VelocityReality(extent=extent)
V = VR.teleport(point=point)
print(V)
print(">===========< Mamma Mia Velocity Reality test complete >==========<")