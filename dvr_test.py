from mamma_mia import WorldExtent, Point, Reality
print("<=========> starting Mamma Mia Velocity Reality test run <===========>")
extent = WorldExtent(lat_max=25,
                lat_min=22,
                lon_min=-26,
                lon_max=-22,
                depth_max=200,
                time_start="2024-08-01T00:00:00",
                time_end="2024-08-07T00:00:00"
                )
point = Point(latitude= 23.8,
              longitude=-24.142,
              depth=25.0,
              dt="2024-08-03T00:00:00",

)

DVR = Reality.for_glidersim(extent=extent,verbose=True)
Real = DVR.teleport(point=point)
print(Real)
print(">===========< Mamma Mia Velocity Reality test complete >==========<")