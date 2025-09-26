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

import gsw
import numpy as np
from attrs import define

@define
class ConvertedTSP:
    Temperature: np.ndarray
    Salinity: np.ndarray
    Pressure: np.ndarray

    @classmethod
    def ps_pt_2_it_ps(cls,practical_salinity:np.ndarray,
                potential_temperature:np.ndarray,
                depth:np.ndarray,
                latitude:np.ndarray,
                longitude:np.ndarray):

        """
        converts:
         - potential temperature to insitu temperature
         - practical salinity to practial salinity
         - depth to pressure
        Args:
            practical_salinity:
            potential_temperature:
            depth:
            latitude:
            longitude:

        Returns:
            dict containing insitu temperature, conductivity, pressure
        """

        pressure = gsw.p_from_z(z=-depth,lat=latitude)

        abs_salinity = gsw.SA_from_SP(SP=practical_salinity, p=pressure,lon=longitude,lat=latitude)

        conservative_temperature = gsw.CT_from_pt(SA=abs_salinity,pt=potential_temperature)

        insitu_temperature = gsw.t_from_CT(SA=abs_salinity,CT=conservative_temperature,p=pressure)

        return cls(Temperature=insitu_temperature,
                   Salinity=practical_salinity,
                   Pressure=pressure)

    @classmethod
    def as_ct_2_it_ps(cls,
                   absolute_salinity: np.ndarray,
                   conservative_temperature: np.ndarray,
                   depth: np.ndarray,
                   latitude: np.ndarray,
                   longitude: np.ndarray):
        """
        converts:
         - conservative temperature to insitu temperature
         - absolute salinity to practical salinity
         - depth to pressure
        Args:
            conservative_temperature:
            absolute_salinity:
            depth:
            latitude:
            longitude:

        Returns:
            dict containing insitu temperature, conductivity, pressure
        """

        pressure = gsw.p_from_z(z=-depth, lat=latitude)

        insitu_temperature = gsw.t_from_CT(SA=absolute_salinity, CT=conservative_temperature, p=pressure)

        practical_salinity = gsw.SP_from_SA(SA=absolute_salinity,p=pressure,lat=latitude,lon=longitude)

        return cls(Temperature=insitu_temperature,
                   Salinity=practical_salinity,
                   Pressure=pressure)
@define
class ConvertedP:
    Pressure: np.ndarray

    @classmethod
    def d_2_p(cls, depth: np.ndarray,latitude: np.ndarray):
        """
        converts: depths to pressures
        Args:
            depth:
            latitude:

        Returns:

        """
        return cls(Pressure=gsw.p_from_z(z=-depth, lat=latitude))

