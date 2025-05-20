import glidersim
import glidersim.configuration
import glidersim.environments
import latlon

# Define a glider model. In this case a Slocum shallow 100 m.
#glider_model = glidersim.glidermodels.Shallow100mGliderModel()
glider_model = glidersim.glidermodels.DeepExtendedGliderModel()
# Set the glider flight parameters.
glider_model.initialise_gliderflightmodel(Cd0=0.20, mg=73.3, Vg=71.542e-3, T1=2052, T2=-35.5, T3=0.36)

# The bathymetry is read from a netcdf file. Set the names of the fields that nead to be read.
glidersim.environments.GliderData.NC_ELEVATION_NAME='elevation'
glidersim.environments.GliderData.NC_ELEVATION_FACTOR=-1
glidersim.environments.GliderData.NC_LAT_NAME='lat'
glidersim.environments.GliderData.NC_LON_NAME='lon'

# Tell dbdreader where to get the cache files from
glidersim.environments.GliderData.DBDREADER_CACHEDIR = 'data/cac'

# Use Mamma Mia to get velocities
environment_model = glidersim.environments.VelocityRealityModel("comet", download_time=24,
                                              gliders_directory='data',
                              bathymetry_filename='gebco_2024_n38.9795_s6.8994_w-30.6299_e-1.626.nc')
# mooring eb1l2
#lat = 23.8
#lon = -24.142
# mooring ebh1
lat = 27.2225
lon = -15.4225
Nmea_lon,Nmea_lat = latlon.convertToNmea(x=lon,y=lat)


# Create a configuration dictionary
conf = glidersim.configuration.Config('rapid-mooring.mi',                # the mission name to run
                                      description="ebh2",       # descriptive text used in the output file
                                      datestr='20230303',       # start date of simulation
                                      timestr='12:00',          # and time
                                      lat_ini=Nmea_lat,#5418.9674,
                                      lon_ini=Nmea_lon,#724.5902,     # starting longitude
                                      mission_directory='data/RAPID-mooring',  # where the missions and mafiles directories are found
                                      output='ebh2-mooring.nc',             # name of output file (pickled files (.pck) can also be used
                                      sensor_settings= dict(c_wpt_lat=Nmea_lat,#5418.000,
                                                            c_wpt_lon=Nmea_lon,# 725.800,
                                                            m_water_vx=0.0,
                                                            m_water_vy=0.0),
                                      special_settings={'glider.gps.acquiretime':100., # how long the GPS should take to get a reading
                                                        'mission_initialisation_time':400,
                                                        "initial_heading": 225}, # how much time the glider needs to initialise.
                                      mission_start="pickup")    # if not set, a new mission is assumed, otherwise it is a continuation of
                                                 # a previous dive.

# Create a GliderMission object, specifying the glider hardware and environment.
GM=glidersim.glidersim.GliderMission(conf,verbose=True,
                                     glider_model=glider_model,
                                     environment_model = environment_model)
# load the mission and show the contents.
GM.loadmission(verbose=True)

# Run the simulation with 0.5 seconds time step. The glider CPU cycle
# is set to 4 seconds. We simulate only 7 hours, and show some
# diagnostic output.
#GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=12/24, end_on_surfacing=False, verbose=True)
GM.run(dt=0.5,CPUcycle=4,maxSimulationTime=1, end_on_surfacing=False, verbose=True)
# Save the results in a file for later analysis
GM.save()
