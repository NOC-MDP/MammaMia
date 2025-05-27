import gsw
import numpy as np
from attrs import define

@define
class ConvertedTCP:
    TEMP: np.ndarray
    CNDC: np.ndarray
    PRES: np.ndarray

    @classmethod
    def from_ps_pt(cls,practical_salinity:np.ndarray,
                potential_temperature:np.ndarray,
                depth:np.ndarray,
                latitude:np.ndarray,
                longitude:np.ndarray):

        """
        converts:
         - potential temperature to insitu temperature
         - practical salinity to conductivity
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

        conductivity = gsw.C_from_SP(SP=practical_salinity,t=insitu_temperature,p=pressure)

        return cls(TEMP=insitu_temperature,
                   CNDC=conductivity,
                   PRES=pressure)

    @classmethod
    def from_as_ct(cls,
                   absolute_salinity: np.ndarray,
                   conservative_temperature: np.ndarray,
                   depth: np.ndarray,
                   latitude: np.ndarray,
                   longitude: np.ndarray):
        """
        converts:
         - conservative temperature to insitu temperature
         - absolute salinity to conductivity
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

        conductivity = gsw.C_from_SP(SP=practical_salinity, t=insitu_temperature, p=pressure)

        return cls(TEMP=insitu_temperature,
                   CNDC=conductivity,
                   PRES=pressure)