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

import datetime
import os
import shutil
import tomllib

from loguru import logger

try:
    import glidersim.configuration
    import glidersim.environments
    import glidersim.glidermodels
    import latlon
    from glidersim.environments import VelocityRealityModel
    from glidersim.glidersim import GliderMission
except ImportError as e:
    logger.debug(f"optional dependency glidersim is not installed: {e}")


def simulate(spec_file: str):
    """

    Args:
        spec_file

    Returns: builder class containing a GliderMission object

    """
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]
    mission_parameters = spec["glidersim"]["mission_parameters"]
    # create new mission directory using example mission template
    if mission_parameters["mission_type"] == "virtual_mooring":
        if mission_parameters["spiral"]:
            shutil.copytree(
                f"example_simulator_missions{os.sep}virtual_mooring_spiral",
                f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}",
                dirs_exist_ok=True,
            )
        else:
            shutil.copytree(
                f"example_simulator_missions{os.sep}virtual_mooring",
                f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}",
                dirs_exist_ok=True,
            )
        # update mi file name with mission name
        os.rename(
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}missions{os.sep}virtual-mooring.mi",
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}missions{os.sep}{mission_parameters['mission_name']}.mi",
        )
    elif mission_parameters["mission_type"] == "follow_waypoints":
        shutil.copytree(
            f"example_simulator_missions{os.sep}waypoints",
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}",
            dirs_exist_ok=True,
        )
        # update mi file name with mission name
        os.rename(
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}missions{os.sep}waypoints.mi",
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}missions{os.sep}{mission_parameters['mission_name']}.mi",
        )

    else:
        raise Exception(f"unknown mission type: {mission_parameters['mission_type']}")

    # Tell dbdreader where to get the cache files from
    glidersim.environments.GliderData.DBDREADER_CACHEDIR = (
        f"{mission_parameters['data_dir']}{os.sep}cac"
    )
    match spec["glidersim"]["sim_model"]["glider_model"]:
        case "DEEP" | "DEEPEXTENDED":
            glider = glidersim.glidermodels.DeepExtendedGliderModel()
        case "100M" | "SHALLOW100M":
            glider = glidersim.glidermodels.Shallow100mGliderModel()
        case "200M" | "SHALLOW200M":
            glider = glidersim.glidermodels.Shallow200mExtendedGliderModel()
        case _:
            raise Exception(
                f"Unknown model {spec['glidersim']['sim_model']['glider_model']}"
            )
    flight_model = spec["glidersim"]["flight_model"]
    glider.initialise_gliderflightmodel(
        Cd0=flight_model["Cd0"],
        mg=flight_model["mg"],
        Vg=flight_model["Vg"],
        T1=flight_model["T1"],
        T2=flight_model["T2"],
        T3=flight_model["T3"],
    )
    env_mod = VelocityRealityModel(
        glider_name=spec["glider_name"],
        download_time=24,
        gliders_directory=mission_parameters["data_dir"],
        bathymetry_filename=spec["glidersim"]["bathymetry"]["file_path"],
        spec_file=spec_file,
    )
    nmea_lon, nmea_lat = latlon.convertToNmea(
        x=mission_parameters["lon_ini"], y=mission_parameters["lat_ini"]
    )
    sensor_settings = dict(
        c_wpt_lat=mission_parameters["lat_ini"],
        c_wpt_lon=mission_parameters["lon_ini"],
        m_water_vx=0,
        m_water_vy=0,
    )
    special_settings = dict(initial_heading=mission_parameters["initial_heading"])
    # Create a configuration dictionary
    dt = datetime.datetime.strptime(
        mission_parameters["datetime_str"], "%Y-%m-%dT%H:%M:%S:Z"
    )
    datestr = dt.strftime("%Y%m%d")
    timestr = dt.strftime("%H:%M")
    conf = glidersim.configuration.Config(
        missionName=mission_parameters["mission_name"]
        + ".mi",  # the mission name to run
        description=mission_parameters[
            "description"
        ],  # descriptive text used in the output file
        datestr=datestr,  # start date of simulation
        timestr=timestr,  # and time
        lat_ini=nmea_lat,
        lon_ini=nmea_lon,  # starting longitude
        mission_directory=f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}",
        # where the missions and mafiles directories are found
        output=f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}{mission_parameters['mission_name']}.nc",
        # name of output file (pickled files (.pck) can also be used
        sensor_settings=sensor_settings,
        special_settings=special_settings,
    )

    gm = glidersim.glidersim.GliderMission(
        conf, verbose=True, glider_model=glider, environment_model=env_mod
    )

    # prepare the mission files for the virtual mooring plan
    if mission_parameters["dive_depth"] > 1000:
        raise Exception(f"no glider model capable of greater than 1000 metre depths")

    # update depth and number of dives in yo file
    with open(
        f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}mafiles{os.sep}yo10.ma",
        "r",
    ) as f:
        yo = f.readlines()
    for i in range(yo.__len__()):
        if "b_arg: d_target_depth(m)" in yo[i]:
            parts = yo[i].split(" ")
            parts[-1] = str(mission_parameters["dive_depth"]) + "\n"
            yo[i] = " ".join(parts)

    with open(
        f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}mafiles{os.sep}yo10.ma",
        "w",
    ) as f:
        f.writelines(yo)
    if mission_parameters["mission_type"] == "virtual_mooring":
        # update waypoints in goto file
        with open(
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}mafiles{os.sep}goto_l10.ma",
            "r",
        ) as f:
            goto = f.readlines()
        for i in range(goto.__len__()):
            if "<end:waypoints>" in goto[i]:
                new_waypoint = f"{gm.gs['m_lat']} {gm.gs['m_lon']}\n"
                goto[i - 1] = new_waypoint
                goto[i - 2] = new_waypoint
                goto[i - 3] = new_waypoint
        with open(
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}mafiles{os.sep}goto_l10.ma",
            "w",
        ) as f:
            f.writelines(goto)

    elif mission_parameters["mission_type"] == "follow_way_points":
        # convert waypoint lats/lons to nmea format
        nmea_lats = []
        nmea_lons = []
        if mission_parameters["lat_wp"].__len__() == 0:
            raise Exception("no lat waypoints specified in spec file")
        if mission_parameters["lon_wp"].__len__() == 0:
            raise Exception("no lon waypoints specified in spec file")
        for i in range(mission_parameters["lat_wp"].__len__()):
            nmea_lat, nmea_lon = latlon.convertToNmea(
                x=mission_parameters["lon_wp"][i], y=mission_parameters["lat_wp"][i]
            )
            nmea_lats.append(nmea_lat)
            nmea_lons.append(nmea_lon)

        # update waypoints in goto file
        with open(
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}mafiles{os.sep}goto_l10.ma",
            "r",
        ) as f:
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

        with open(
            f"{mission_parameters['data_dir']}{os.sep}{mission_parameters['mission_directory']}{os.sep}mafiles{os.sep}goto_l10.ma",
            "w",
        ) as f:
            f.writelines(new_goto)
    return gm


def run_mission(gm, spec_file: str):
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
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]["glidersim"]
    logger.info(f"running mission {spec['mission_parameters']['mission_name']}")
    gm.loadmission(verbose=spec["run_parameters"]["verbose"])
    gm.run(
        dt=spec["run_parameters"]["dt"],
        CPUcycle=spec["run_parameters"]["CPUcycle"],
        maxSimulationTime=spec["run_parameters"]["maxSimulationTime"],
        end_on_surfacing=spec["run_parameters"]["end_on_surfacing"],
        end_on_grounding=spec["run_parameters"]["end_on_grounding"],
        verbose=spec["run_parameters"]["verbose"],
    )
    logger.success(f"mission {spec['mission_parameters']['mission_name']} complete")


def save_mission(gm, spec_file: str):
    """

    Returns: none

    """
    with open(spec_file, "rb") as f:
        raw = tomllib.load(f)
    spec = raw["specification"]["glidersim"]
    logger.info(f"saving mission {spec['mission_parameters']['mission_name']}")
    gm.save()
    logger.success(f"mission {spec['mission_parameters']['mission_name']} saved")
