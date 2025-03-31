import copy
from loguru import logger
import sys
import attrs.exceptions
import pytest
from mamma_mia import create_platform_class,parameter_inventory,Parameter, create_sensor_class
from mamma_mia import Extent, Point, Reality
from cattrs import structure
# TODO add more tests, e.g. one with time parameter and check inventory creation etc.

# Sample test data
PLATFORM_DATA = {
                "nvs_platform_id": "B7600002",
                "platform_type": "eagle",
                "platform_manufacturer": "Feel Good Inc",
                "platform_model_name": "K2",
                "platform_name": "TestGlider",
                "platform_family" : "coastal_ocean_glider",
                "platform_serial_number": "TG-001",
                "platform_owner": "ACME",
                "wmo_platform_code": 57207583,
                "data_type": "OG time-series data"
}

SENSOR_DATA = {
                "sensor_serial_number": "SN-123",
                "sensor_name": "CTD-Sensor-1",
                "instrument_type": "water temperature sensor",
                "sensor_manufacturer": "Eagle Instruments",
                "model_name": "EI Glider Payload (GPCTD) CTD",
                "sensor_model": "EI Glider Payload (GPCTD) CTD",
                "max_sample_rate": 5,
                "parameters": {
                    "TEMP": 1,
                    "CNDC": 1,
                    "PRES": 1
                }
            }

PARAMETER_DATA = {
                "parameter_name": "SAL",
                "standard_name": "sea_water_electrical_conductivity",
                "unit_of_measure": "mhos/m",
                "parameter_definition": "Electrical conductivity of the water body by CTD",
                "seadatanet_parameter": "http://vocab.nerc.ac.uk/collection/P01/current/CNDCST01/",
                "seadatanet_unit_of_measure": "SDN:P06::UECA",
                "source_name": "sci_water_cond",
                "ancillary_variables": "SAL_QC"
            }


@pytest.fixture
def platform_inventory2():
    """Fixture to create a fresh Platforminventory instance for each test."""
    return copy.deepcopy(platform_inventory)


@pytest.fixture
def sensor_inventory2():
    """Fixture to create a fresh Sensorinventory instance for each test."""
    return copy.deepcopy(sensor_inventory)


@pytest.fixture
def parameter_inventory2():
    """Fixture to create a fresh Parameterinventory instance for each test."""
    return copy.deepcopy(parameter_inventory)


# ----------------------------------
# PLATFORM inventory TESTS
# ----------------------------------

def test_add_platform(platform_inventory2):
    """Test adding a new platform to the inventory."""
    platform = structure(PLATFORM_DATA,create_platform_class(frozen_mode=True))
    platform_inventory2.add_platform(platform_type="glider", platform=platform)

    assert "TestGlider" in platform_inventory2._glider
    assert platform_inventory2._glider["TestGlider"].platform_serial_number == "TG-001"


def test_get_platform(platform_inventory2):
    """Test retrieving a platform by name."""
    platform = structure(PLATFORM_DATA,create_platform_class(frozen_mode=True))
    platform_inventory2.add_platform("glider", platform=platform)

    retrieved = platform_inventory2.create_entity("Testy McTestFace", "glider", "TestGlider")
    assert retrieved.platform_serial_number == "TG-001"


def test_modify_platform(platform_inventory2):
    """Ensure modification of an existing platform is restricted."""
    platform = structure(PLATFORM_DATA,create_platform_class(frozen_mode=True))
    platform_inventory2.add_platform("glider", platform=platform)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        platform_inventory2._glider["TestGlider"].platform_serial_number = "MODIFIED"

def test_remove_platform(platform_inventory2):
    """Test removing a platform."""
    platform = structure(PLATFORM_DATA,create_platform_class(frozen_mode=True))
    platform_inventory2.add_platform("glider", platform=platform)

    platform_inventory2.remove_platform("glider", "TestGlider")

    assert "TestGlider" not in platform_inventory2._glider


# ----------------------------------
# SENSOR inventory TESTS
# ----------------------------------

def test_add_sensor(sensor_inventory2):
    """Test adding a new sensor to the inventory."""
    sensor = structure(SENSOR_DATA,create_sensor_class(frozen_mode=True))
    sensor_inventory2.add_sensor("CTD", sensor)

    assert "CTD-Sensor-1" in sensor_inventory2._CTD


def test_get_sensor(sensor_inventory2):
    """Test retrieving a sensor by name."""
    sensor = structure(SENSOR_DATA, create_sensor_class(frozen_mode=True))
    sensor_inventory2.add_sensor("CTD", sensor)

    retrieved = sensor_inventory2.get_sensor("CTD", "CTD-Sensor-1")
    assert retrieved.sensor_serial_number == "SN-123"

def test_modify_sensor(sensor_inventory2):
    """Ensure modification of an existing sensor is restricted."""
    sensor = structure(SENSOR_DATA, create_sensor_class(frozen_mode=True))
    sensor_inventory2.add_sensor("CTD", sensor)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        sensor_inventory2._CTD["CTD-Sensor-1"].sensor_serial_number = "MODIFIED"

def test_remove_sensor(sensor_inventory2):
    """Test removing a sensor."""
    sensor = structure(SENSOR_DATA, create_sensor_class(frozen_mode=True))
    sensor_inventory2.add_sensor("CTD", sensor)

    sensor_inventory2.remove_sensor("CTD", "CTD-Sensor-1")

    assert "CTD-Sensor-1" not in sensor_inventory2._CTD


# ----------------------------------
# PARAMETER inventory TESTS
# ----------------------------------

def test_add_parameter(parameter_inventory2):
    """Test adding a new parameter to the inventory."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_inventory2.add_parameter("environmental", parameter)

    assert "SAL" in parameter_inventory2._environmental


def test_get_parameter(parameter_inventory2):
    """Test retrieving a parameter by name."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_inventory2.add_parameter("environmental", parameter)

    retrieved = parameter_inventory2.get_parameter("environmental", "SAL")
    assert retrieved.unit_of_measure == "mhos/m"

def test_modify_parameter(parameter_inventory2):
    """Ensure modification of an existing parameter is restricted."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_inventory2.add_parameter("environmental", parameter)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        parameter_inventory2._environmental["SAL"].unit_of_measure = "MODIFIED"


def test_remove_parameter(parameter_inventory2):
    """Test removing a parameter."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_inventory2.add_parameter("environmental", parameter)

    parameter_inventory2.remove_parameter("environmental", "SAL")

    assert "SAL" not in parameter_inventory2._environmental


import pytest
from mamma_mia import platform_inventory, sensor_inventory
from mamma_mia import Campaign
from mamma_mia import Creator, Publisher, Contributor


def test_campaign_creation():
    campaign = Campaign(name="SE_Greenland_2019",
                        description="single slocum glider deployment off South East Greenland",
                        verbose=True)
    assert campaign.name == "SE_Greenland_2019"
    assert campaign.description == "single slocum glider deployment off South East Greenland"


def test_catalog_operations():
    campaign = Campaign(name="Test_Campaign", description="Test Description")
    initial_sources = campaign.catalog.get_sources_list().copy()
    campaign.catalog.set_priority(source="MSM", priority=3)
    updated_sources = campaign.catalog.get_sources_list()
    assert "MSM" in updated_sources
    assert updated_sources != initial_sources


def test_platform_inventory():
    platform_types = platform_inventory.list_platform_types()
    assert isinstance(platform_types, list)
    assert "glider" in platform_types

    glider_platforms = platform_inventory.list_platforms(platform_type='glider')
    assert isinstance(glider_platforms, list)


def test_platform_creation():
    churchill = platform_inventory.create_entity(entity_name="Churchill_withCTD", platform="Churchill",
                                                 platform_type="glider")
    assert churchill.platform == "Churchill"
    assert churchill.platform_type == "glider"


def test_sensor_inventory():
    glider_CTD = sensor_inventory.create_entity(entity_name="ctd_for_churchill", sensor_type="CTD", sensor_ref="9100")
    glider_CTD.update_sample_rate(sample_rate=10)
    assert glider_CTD.sample_rate == 10


def test_sensor_registration():
    churchill = platform_inventory.create_entity(entity_name="Churchill_withCTD", platform="Churchill",
                                                 platform_type="glider")
    glider_CTD = sensor_inventory.create_entity(entity_name="ctd_for_churchill", sensor_type="CTD", sensor_ref="9100")
    churchill.register_sensor(sensor=glider_CTD)
    assert glider_CTD in churchill.list_registered_sensors()


def test_campaign_platform_registration():
    campaign = Campaign(name="Test_Campaign", description="Test Description")
    churchill = platform_inventory.create_entity(entity_name="Churchill_noCTD", platform="Churchill",
                                                 platform_type="glider")
    campaign.register_platform(platform=churchill, name="Churchill_noCTD")
    assert "Churchill_noCTD" in campaign.platforms


def test_mission_creation():
    campaign = Campaign(name="Test_Campaign", description="Test Description")
    creator = Creator(email="thopri@noc.ac.uk", institution="NOCS", name="thopri", creator_type="", url="noc.ac.uk")
    publisher = Publisher(email="glidersbodc@noc.ac.uk", institution="NOCS", name="NOCS", type="DAC", url="bodc.ac.uk")
    contributor = Contributor(email="thopri@noc.ac.uk", name="thopri", role_vocab="BODC database", role="Collaborator")
    churchill = platform_inventory.create_entity(entity_name="Churchill_withCTD", platform="Churchill",
                                                 platform_type="glider")
    campaign.register_platform(platform=churchill, name="Churchill_withCTD")
    campaign.add_mission(mission_name="SEG19_01", title="Churchill with CTD deployment off South East Greenland",
                         summary="single glider deployed to undertake 15 dives to 200m",
                         platform_name="Churchill_withCTD",
                         trajectory_path="comet-mm1.nc", creator=creator, publisher=publisher, contributor=contributor)
    assert "SEG19_01" in campaign.missions


def test_mission_execution():
    campaign = Campaign(name="Test_Campaign", description="Test Description")
    campaign.build_missions()
    campaign.run()
    assert campaign.missions  # Ensure missions are not empty


def test_mission_visualization():
    campaign = Campaign(name="Test_Campaign", description="Test Description")
    mission_name = "SEG19_01"
    campaign.missions[mission_name].plot_trajectory()
    campaign.missions[mission_name].show_payload()


def test_export():
    campaign = Campaign(name="Test_Campaign", description="Test Description")
    campaign.export()
    mission_name = "SEG19_01"
    campaign.missions[mission_name].export_to_nc()

def setup_logger():
    logger.remove()
    logger.add(sys.stdout, format='{time:YYYY-MM-DDTHH:mm:ss} - <level>{level}</level> - {message}', level="INFO")

def test_extent_creation():
    extent = Extent(max_lat=58.0,
                    min_lat=56.0,
                    min_lng=6.0,
                    max_lng=7.0,
                    max_depth=200,
                    start_dt="2023-01-01T00:00:00",
                    end_dt="2023-01-07T00:00:00"
                    )
    assert extent.max_lat == 58.0
    assert extent.min_lat == 56.0
    assert extent.min_lng == 6.0
    assert extent.max_lng == 7.0
    assert extent.max_depth == 200
    assert extent.start_dt == "2023-01-01T00:00:00"
    assert extent.end_dt == "2023-01-07T00:00:00"

def test_point_creation():
    point = Point(latitude=57.1,
                  longitude=6.4,
                  depth=12.0,
                  dt="2023-01-03T00:00:00",
    )
    assert point.latitude == 57.1
    assert point.longitude == 6.4
    assert point.depth == 12.0
    assert point.dt == "2023-01-03T00:00:00"

def test_reality_teleport():
    setup_logger()
    extent = Extent(max_lat=58.0,
                    min_lat=56.0,
                    min_lng=6.0,
                    max_lng=7.0,
                    max_depth=200,
                    start_dt="2023-01-01T00:00:00",
                    end_dt="2023-01-07T00:00:00"
                    )
    point = Point(latitude=57.1,
                  longitude=6.4,
                  depth=12.0,
                  dt="2023-01-03T00:00:00",
    )
    DVR = Reality(extent=extent, verbose=True)
    Real = DVR.teleport(point=point)
    assert Real is not None
