import os
import glidersim.configuration
import glidersim.environments
import glidersim.glidermodels
import latlon
import datetime
from attrs import define,frozen
from cattr import unstructure
import glidersim.glidermodels
from glidersim.environments import VelocityRealityModel
from glidersim.glidersim import GliderMission

@frozen
class FlightParameters:
    Cd0: float = 0.2
    mg:float = 73.3
    Vg:float = 71.542e-3
    T1:float = 2052
    T2:float = -35.5
    T3:float = 0.36

@frozen
class BathymetryParameters:
    elevation_name: str = 'elevation'
    elevation_factor: int = -1
    lat_name: str = 'lat'
    lon_name: str = 'lon'
    file_path: str = 'gebco_2024_n38.9795_s6.8994_w-30.6299_e-1.626.nc'

    @classmethod
    def for_mission(cls):
        bathy = BathymetryParameters()
        glidersim.environments.GliderData.NC_ELEVATION_NAME = bathy.elevation_name
        glidersim.environments.GliderData.NC_ELEVATION_FACTOR = bathy.elevation_factor
        glidersim.environments.GliderData.NC_LAT_NAME = bathy.lat_name
        glidersim.environments.GliderData.NC_LON_NAME = bathy.lon_name
        return bathy

@frozen
class SensorSettings:
    c_wpt_lat: float
    c_wpt_lon: float
    m_water_vx: float
    m_water_vy: float

@frozen
class SpecialSettings:
    initial_heading: float
    glider_gps_acquiretime: float = 100.00
    mission_initialisation_time: float = 400

class ModelBuilder:
    @classmethod
    def from_string(cls,model:str) -> glidersim.glidermodels.BaseGliderModel:
        match model:
            case "DEEP" | "DEEPEXTENDED":
                return glidersim.glidermodels.DeepExtendedGliderModel()
            case "100M" | "SHALLOW100M":
                return glidersim.glidermodels.Shallow100mGliderModel()
            case "200M" | "SHALLOW200M":
                return glidersim.glidermodels.Shallow200mExtendedGliderModel()
            case _:
                raise Exception(f"Unknown model {model}")

@define
class MissionBuilder:
    glider_mission: GliderMission

    @classmethod
    def create_mission(cls,
                       mission_name:str,
                       glider_model:str,
                       glider_name:str,
                       description:str,
                       datetime_str:str,
                       lat_ini:float,
                       lon_ini:float,
                       inital_heading:float,
                       mission_directory:str,
                       mission_start:str = "pickup",
                       fp:FlightParameters = FlightParameters(),
                       bathy:BathymetryParameters= BathymetryParameters.for_mission()) -> "MissionBuilder":

        glider = ModelBuilder.from_string(glider_model)
        glider.initialise_gliderflightmodel(Cd0=fp.Cd0,
                                                  mg=fp.mg,
                                                  Vg=fp.Vg,
                                                  T1=fp.T1,
                                                  T2=fp.T2,
                                                  T3=fp.T3)
        env_mod = VelocityRealityModel(glider_name=glider_name,
                                       download_time=24,
                                       gliders_directory='data',
                                       bathymetry_filename=bathy.file_path,
                                       )
        nmea_lon, nmea_lat = latlon.convertToNmea(x=lon_ini, y=lat_ini)
        sensor_settings = SensorSettings(c_wpt_lat=lat_ini,
                                         c_wpt_lon=lon_ini,
                                         m_water_vx=0,
                                         m_water_vy=0,)
        special_settings = SpecialSettings(initial_heading=inital_heading)
        # Create a configuration dictionary
        dt = datetime.datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S:Z")
        datestr = dt.strftime("%Y%m%d")
        timestr = dt.strftime("%H:%M")
        conf = glidersim.configuration.Config(missionName=mission_name,  # the mission name to run
                                              description=description,  # descriptive text used in the output file
                                              datestr=datestr,  # start date of simulation
                                              timestr=timestr,  # and time
                                              lat_ini=nmea_lat,  # 5418.9674,
                                              lon_ini=nmea_lon,  # 724.5902,     # starting longitude
                                              mission_directory=mission_directory,
                                              # where the missions and mafiles directories are found
                                              output=f"{mission_directory}{os.sep}{mission_name}.nc",
                                              # name of output file (pickled files (.pck) can also be used
                                              sensor_settings=unstructure(sensor_settings),
                                              special_settings=unstructure(special_settings),
                                              # how much time the glider needs to initialise.
                                              mission_start=mission_start)  # if not set, a new mission is assumed, otherwise it is a continuation of a previous dive.

        gm = glidersim.glidersim.GliderMission(conf,verbose=True,glider_model=glider,environment_model=env_mod)
        return cls(glider_mission=gm)

    def run(self,dt=0.5,CPUcycle=4,maxSimulationTime=1, end_on_surfacing=False, end_on_grounding=False,verbose=True):
        self.glider_mission.run(dt=dt,
                                CPUcycle=CPUcycle,
                                maxSimulationTime=maxSimulationTime,
                                end_on_surfacing=end_on_surfacing,
                                end_on_grounding=end_on_grounding,
                                verbose=verbose)
    def save(self):
        self.glider_mission.save()




