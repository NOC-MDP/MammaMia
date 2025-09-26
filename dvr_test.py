# Copyright 2025 National Oceanography Centre
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#  http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from mamma_mia import WorldExtent, Point, Reality
print("<=========> starting Mamma Mia Velocity Reality test run <===========>")
extent = WorldExtent(lat_max=25.0,
                lat_min=22.0,
                lon_min=-26.0,
                lon_max=-22.0,
                depth_max=200.0,
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