import gsw
import numpy as np

def convert_tsp(practical_salinity:np.ndarray,
                potential_temperature:np.ndarray,
                depth:np.ndarray,
                latitude:np.ndarray,
                longitude:np.ndarray) -> dict[str,np.ndarray]:
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
        dict containting insitu temperature, conductivity, pressure
    """

    pressure = gsw.p_from_z(z=-depth,lat=latitude)

    abs_salinity = gsw.SA_from_SP(SP=practical_salinity, p=pressure,lon=longitude,lat=latitude)

    conservative_temperature = gsw.CT_from_pt(SA=abs_salinity,pt=potential_temperature)

    insitu_temperature = gsw.t_from_CT(SA=abs_salinity,CT=conservative_temperature,p=pressure)

    conductivity = gsw.C_from_SP(SP=practical_salinity,t=insitu_temperature,p=pressure)

    return {"TEMP":insitu_temperature,
            "CNDC":conductivity,
            "PRES":pressure
            }

