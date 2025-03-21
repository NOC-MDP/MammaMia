import copy

import attrs.exceptions
import pytest
from mamma_mia import platform_inventory, create_platform_class,parameter_inventory,Parameter,sensor_inventory, create_sensor_class
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
