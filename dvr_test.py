from mamma_mia import Extent, Point, Reality
from loguru import logger
import sys
print("<=========> starting Mamma Mia Velocity Reality test run <===========>")
logger.remove()
logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}',level="INFO")
extent = Extent(max_lat=25,
                min_lat=22,
                min_lng=-26,
                max_lng=-22,
                max_depth=200,
                start_dt="2024-08-01T00:00:00",
                end_dt="2024-08-07T00:00:00"
                )
point = Point(latitude= 23.8,
              longitude=-24.142,
              depth=25.0,
              dt="2024-08-03T00:00:00",

)

DVR = Reality(extent=extent,verbose=True)
Real = DVR.teleport(point=point)
print(Real)
print(">===========< Mamma Mia Velocity Reality test complete >==========<")