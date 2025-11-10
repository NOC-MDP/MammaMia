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
import shutil
from loguru import logger

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

class GliderBuilder:
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
class GliderMissionBuilder:
    glider_mission: GliderMission

    @classmethod
    def virtual_mooring(cls,
                       mission_name:str,
                       glider_model:str,
                       glider_name:str,
                       description:str,
                       datetime_str:str,
                       lat_ini:float,
                       lon_ini:float,
                       inital_heading:float,
                       dive_depth:float,
                       mission_directory:str,
                       data_dir:str = "data",
                       spiral:bool = False,
                       fp:FlightParameters = FlightParameters(),
                       bathy:BathymetryParameters= BathymetryParameters.for_mission()) -> "GliderMissionBuilder":
        """

        Args:
            spiral:
            dive_depth:
            mission_name:
            glider_model:
            glider_name:
            description:
            datetime_str:
            lat_ini:
            lon_ini:
            inital_heading:
            mission_directory:
            data_dir:
            fp:
            bathy:

        Returns: builder class containing a GliderMission object

        """
        # create new mission directory using example mission template
        if spiral:
            shutil.copytree(f"example_missions{os.sep}virtual_mooring_spiral", f"{data_dir}{os.sep}{mission_directory}",
                            dirs_exist_ok=True)
        else:
            shutil.copytree(f"example_missions{os.sep}virtual_mooring", f"{data_dir}{os.sep}{mission_directory}", dirs_exist_ok=True)
        # update mi file name with mission name
        os.rename(f"{data_dir}{os.sep}{mission_directory}{os.sep}missions{os.sep}virtual-mooring.mi",
                  f"{data_dir}{os.sep}{mission_directory}{os.sep}missions{os.sep}{mission_name}.mi")

        # Tell dbdreader where to get the cache files from
        glidersim.environments.GliderData.DBDREADER_CACHEDIR = f'{data_dir}{os.sep}cac'
        glider = GliderBuilder.from_string(glider_model)
        glider.initialise_gliderflightmodel(Cd0=fp.Cd0,
                                                  mg=fp.mg,
                                                  Vg=fp.Vg,
                                                  T1=fp.T1,
                                                  T2=fp.T2,
                                                  T3=fp.T3)
        env_mod = VelocityRealityModel(glider_name=glider_name,
                                       download_time=24,
                                       gliders_directory=data_dir,
                                       bathymetry_filename=bathy.file_path,
                                       env_source = "MSM"
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
        conf = glidersim.configuration.Config(missionName=mission_name+".mi",  # the mission name to run
                                              description=description,  # descriptive text used in the output file
                                              datestr=datestr,  # start date of simulation
                                              timestr=timestr,  # and time
                                              lat_ini=nmea_lat,
                                              lon_ini=nmea_lon,  # starting longitude
                                              mission_directory=f"{data_dir}{os.sep}{mission_directory}",
                                              # where the missions and mafiles directories are found
                                              output=f"{data_dir}{os.sep}{mission_directory}{os.sep}{mission_name}.nc",
                                              # name of output file (pickled files (.pck) can also be used
                                              sensor_settings=unstructure(sensor_settings),
                                              special_settings=unstructure(special_settings),
                                              )

        gm = glidersim.glidersim.GliderMission(conf,verbose=True,glider_model=glider,environment_model=env_mod)

        # prepare the mission files for the virtual mooring plan
        if dive_depth > 1000:
            raise Exception(f"no glider model capable of greater than 1000 metre depths")

        # update depth and number of dives in yo file
        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}yo10.ma",'r') as f:
            yo = f.readlines()
        for i in range(yo.__len__()):
            if "b_arg: d_target_depth(m)" in yo[i]:
                parts = yo[i].split(" ")
                parts[-1] = str(dive_depth) +"\n"
                yo[i] = " ".join(parts)

        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}yo10.ma",'w') as f:
            f.writelines(yo)

        # update waypoints in goto file
        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}goto_l10.ma",'r') as f:
            goto = f.readlines()
        for i in range(goto.__len__()):
            if "<end:waypoints>" in goto[i]:
                new_waypoint = f"{gm.gs['m_lat']} {gm.gs['m_lon']}\n"
                goto[i - 1] = new_waypoint
                goto[i - 2] = new_waypoint
                goto[i - 3] = new_waypoint
        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}goto_l10.ma",'w') as f:
            f.writelines(goto)

        return cls(glider_mission=gm)

    @classmethod
    def follow_waypoints(cls,
                       mission_name:str,
                       glider_model:str,
                       glider_name:str,
                       description:str,
                       datetime_str:str,
                       lat_ini:float,
                       lon_ini:float,
                       inital_heading:float,
                       dive_depth:float,
                       lat_wp:list[float],
                       lon_wp:list[float],
                       mission_directory:str,
                       data_dir:str = "data",
                       fp:FlightParameters = FlightParameters(),
                       bathy:BathymetryParameters= BathymetryParameters.for_mission()) -> "GliderMissionBuilder":
        """

        Args:
            lon_wp:
            lat_wp:
            dive_depth:
            mission_name:
            glider_model:
            glider_name:
            description:
            datetime_str:
            lat_ini:
            lon_ini:
            inital_heading:
            mission_directory:

            data_dir:
            fp:
            bathy:

        Returns: builder class containing a GliderMission object

        """
        # create new mission directory using example mission template
        shutil.copytree(f"example_missions{os.sep}waypoints", f"{data_dir}{os.sep}{mission_directory}", dirs_exist_ok=True)
        # update mi file name with mission name
        os.rename(f"{data_dir}{os.sep}{mission_directory}{os.sep}missions{os.sep}waypoints.mi",
                  f"{data_dir}{os.sep}{mission_directory}{os.sep}missions{os.sep}{mission_name}.mi")
        # Tell dbdreader where to get the cache files from
        glidersim.environments.GliderData.DBDREADER_CACHEDIR = f'{data_dir}{os.sep}cac'
        glider = GliderBuilder.from_string(glider_model)
        glider.initialise_gliderflightmodel(Cd0=fp.Cd0,
                                                  mg=fp.mg,
                                                  Vg=fp.Vg,
                                                  T1=fp.T1,
                                                  T2=fp.T2,
                                                  T3=fp.T3)
        env_mod = VelocityRealityModel(glider_name=glider_name,
                                       download_time=24,
                                       gliders_directory=data_dir,
                                       bathymetry_filename=bathy.file_path,
                                       env_source="MSM"
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
        conf = glidersim.configuration.Config(missionName=mission_name+".mi",  # the mission name to run
                                              description=description,  # descriptive text used in the output file
                                              datestr=datestr,  # start date of simulation
                                              timestr=timestr,  # and time
                                              lat_ini=nmea_lat,
                                              lon_ini=nmea_lon,  # starting longitude
                                              mission_directory=f"{data_dir}{os.sep}{mission_directory}",
                                              # where the missions and mafiles directories are found
                                              output=f"{data_dir}{os.sep}{mission_directory}{os.sep}{mission_name}.nc",
                                              # name of output file (pickled files (.pck) can also be used
                                              sensor_settings=unstructure(sensor_settings),
                                              special_settings=unstructure(special_settings),
                                              )

        gm = glidersim.glidersim.GliderMission(conf,verbose=True,glider_model=glider,environment_model=env_mod)

        # prepare the mission files for the virtual mooring plan
        if dive_depth > 1000:
            raise Exception(f"no glider model currently capable of greater than 1000 metre depths")

        # update depth in yo file
        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}yo10.ma",'r') as f:
            yo = f.readlines()
        for i in range(yo.__len__()):
            if "b_arg: d_target_depth(m)" in yo[i]:
                parts = yo[i].split(" ")
                parts[-1] = str(dive_depth) +"\n"
                yo[i] = " ".join(parts)

        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}yo10.ma",'w') as f:
            f.writelines(yo)

        # convert waypoint lats/lons to nmea format
        nmea_lats = []
        nmea_lons = []
        for i in range(lat_wp.__len__()):
            nmea_lat, nmea_lon = latlon.convertToNmea(x=lon_wp[i], y=lat_wp[i])
            nmea_lats.append(nmea_lat)
            nmea_lons.append(nmea_lon)

        # update waypoints in goto file
        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}goto_l10.ma",'r') as f:
            goto = f.readlines()
        new_goto = []
        in_waypoint_section = False
        for i in range(goto.__len__()):
            if "<start:waypoints>" in goto[i]:
                new_goto.append(goto[i])
                for j in range(nmea_lats.__len__()):
                    new_goto.append(f"{nmea_lats[j]} {nmea_lons[j]}\n")
                    in_waypoint_section = True
            if "<end:waypoints>" in goto[i]:
                in_waypoint_section = False
            if in_waypoint_section:
                continue
            new_goto.append(goto[i])

        with open(f"{data_dir}{os.sep}{mission_directory}{os.sep}mafiles{os.sep}goto_l10.ma",'w') as f:
            f.writelines(new_goto)

        return cls(glider_mission=gm)



    def run_mission(self,
                    dt=0.5,
                    CPUcycle=4,
                    maxSimulationTime=1,
                    end_on_surfacing=False,
                    end_on_grounding=False,
                    verbose:bool=False):
        """

        Args:
            dt:
            CPUcycle:
            maxSimulationTime:
            end_on_surfacing:
            end_on_grounding:
            verbose:

        Returns: None

        """
        logger.info(f"running mission for {self.glider_mission.mission}")
        self.glider_mission.loadmission(verbose=verbose)
        self.glider_mission.run(dt=dt,
                                CPUcycle=CPUcycle,
                                maxSimulationTime=maxSimulationTime,
                                end_on_surfacing=end_on_surfacing,
                                end_on_grounding=end_on_grounding,
                                verbose=verbose)
        logger.success(f"mission {self.glider_mission.mission} complete")

    def save_mission(self):
        """

        Returns: none

        """
        logger.info(f"saving mission {self.glider_mission.mission}")
        self.glider_mission.save()
        logger.success(f"mission {self.glider_mission.mission} saved")

