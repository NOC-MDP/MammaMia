from dataclasses import FrozenInstanceError

import attrs.exceptions
import pytest
from mamma_mia import PlatformCatalog, Platform, ParameterCatalog,Parameter, SensorCatalog, Sensor
from cattrs import structure
# TODO add more tests, e.g. one with time parameter and check catalog creation etc.

# Sample test data
PLATFORM_DATA = {
                "bodc_platform_model_id": 134,
                "platform_model_id":567,
                "nvs_platform_id": "B7600002",
                "platform_type": "eagle",
                "platform_manufacturer": "Feel Good Inc",
                "platform_model_name": "K2",
                "bodc_platform_id": 456,
                "bodc_platform_type_id": 874,
                "platform_name": "TestGlider",
                "platform_family" : "coastal_ocean_glider",
                "platform_serial_number": "TG-001",
                "platform_owner": "ACME",
                "wmo_platform_code": 57207583,
                "data_type": "OG time-series data"
}

SENSOR_DATA = {
                "sensor_serial_number": "SN-123",
                "bodc_sensor_version_id": 1567,
                "bodc_sensor_id": 734,
                "sensor_name": "CTD-Sensor-1",
                "bodc_sensor_model_id": 223,
                "bodc_sensor_model_registry_id": 211,
                "instrument_type": "water temperature sensor",
                "sensor_manufacturer": "Eagle Instruments",
                "model_name": "EI Glider Payload (GPCTD) CTD",
                "sensor_model": "EI Glider Payload (GPCTD) CTD",
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
def platform_catalog():
    """Fixture to create a fresh PlatformCatalog instance for each test."""
    return PlatformCatalog()


@pytest.fixture
def sensor_catalog():
    """Fixture to create a fresh SensorCatalog instance for each test."""
    return SensorCatalog()


@pytest.fixture
def parameter_catalog():
    """Fixture to create a fresh ParameterCatalog instance for each test."""
    return ParameterCatalog()


# ----------------------------------
# PLATFORM CATALOG TESTS
# ----------------------------------

def test_add_platform(platform_catalog):
    """Test adding a new platform to the catalog."""
    platform = structure(PLATFORM_DATA,Platform)
    platform_catalog.add_platform(platform_type="glider", platform=platform)

    assert "TestGlider" in platform_catalog._glider
    assert platform_catalog._glider["TestGlider"].platform_serial_number == "TG-001"


def test_get_platform(platform_catalog):
    """Test retrieving a platform by name."""
    platform = structure(PLATFORM_DATA,Platform)
    platform_catalog.add_platform("glider", platform=platform)

    retrieved = platform_catalog.get_platform("glider","TestGlider")
    assert retrieved.platform_serial_number == "TG-001"


def test_modify_platform(platform_catalog):
    """Ensure modification of an existing platform is restricted."""
    platform = structure(PLATFORM_DATA,Platform)
    platform_catalog.add_platform("glider", platform=platform)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        platform_catalog._glider["TestGlider"].platform_serial_number = "MODIFIED"

def test_remove_platform(platform_catalog):
    """Test removing a platform."""
    platform = structure(PLATFORM_DATA,Platform)
    platform_catalog.add_platform("glider", platform=platform)

    platform_catalog.remove_platform("glider", "TestGlider")

    assert "TestGlider" not in platform_catalog._glider


# ----------------------------------
# SENSOR CATALOG TESTS
# ----------------------------------

def test_add_sensor(sensor_catalog):
    """Test adding a new sensor to the catalog."""
    sensor = structure(SENSOR_DATA,Sensor)
    sensor_catalog.add_sensor("CTD", sensor)

    assert "CTD-Sensor-1" in sensor_catalog._CTD


def test_get_sensor(sensor_catalog):
    """Test retrieving a sensor by name."""
    sensor = structure(SENSOR_DATA, Sensor)
    sensor_catalog.add_sensor("CTD", sensor)

    retrieved = sensor_catalog.get_sensor("CTD", "CTD-Sensor-1")
    assert retrieved.sensor_serial_number == "SN-123"

def test_modify_sensor(sensor_catalog):
    """Ensure modification of an existing sensor is restricted."""
    sensor = structure(SENSOR_DATA, Sensor)
    sensor_catalog.add_sensor("CTD", sensor)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        sensor_catalog._CTD["CTD-Sensor-1"].sensor_serial_number = "MODIFIED"

def test_remove_sensor(sensor_catalog):
    """Test removing a sensor."""
    sensor = structure(SENSOR_DATA, Sensor)
    sensor_catalog.add_sensor("CTD", sensor)

    sensor_catalog.remove_sensor("CTD", "CTD-Sensor-1")

    assert "CTD-Sensor-1" not in sensor_catalog._CTD


# ----------------------------------
# PARAMETER CATALOG TESTS
# ----------------------------------

def test_add_parameter(parameter_catalog):
    """Test adding a new parameter to the catalog."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_catalog.add_parameter("environmental", parameter)

    assert "SAL" in parameter_catalog._environmental


def test_get_parameter(parameter_catalog):
    """Test retrieving a parameter by name."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_catalog.add_parameter("environmental", parameter)

    retrieved = parameter_catalog.get_parameter("environmental", "SAL")
    assert retrieved.unit_of_measure == "mhos/m"

def test_modify_parameter(parameter_catalog):
    """Ensure modification of an existing parameter is restricted."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_catalog.add_parameter("environmental", parameter)

    with pytest.raises(attrs.exceptions.FrozenInstanceError):
        parameter_catalog._environmental["SAL"].unit_of_measure = "MODIFIED"


def test_remove_parameter(parameter_catalog):
    """Test removing a parameter."""
    parameter = structure(PARAMETER_DATA, Parameter)
    parameter_catalog.add_parameter("environmental", parameter)

    parameter_catalog.remove_parameter("environmental", "SAL")

    assert "SAL" not in parameter_catalog._environmental
