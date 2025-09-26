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

from mamma_mia.platforms import PlatformInventory, sensor_inventory
from mamma_mia.sensors import SensorInventory, parameter_inventory
from mamma_mia.parameters import ParameterInventory
from attrs import frozen

@frozen
class InventoryClass:
    platforms: PlatformInventory = PlatformInventory()
    sensors: SensorInventory = sensor_inventory
    parameters: ParameterInventory = parameter_inventory

    @staticmethod
    def list_inventory_groups():
        return ["platforms", "sensors", "parameters"]

    def list_platform_types(self):
        """
        Lists all available platform types.
        Returns: list of platform types.

        """
        platform_types = []
        for platform in self.platforms.entries.values():
            if platform.platform_type not in platform_types:
                platform_types.append(platform.platform_type)
        return platform_types

    def get_platform_info(self, platform_ref:str):
        """

        Args:
            platform_ref:

        Returns:
        """
        for platform in self.platforms.entries.values():
            if platform.platform_name == platform_ref or platform.platform_serial_number == platform_ref:
                return platform

    def list_sensor_types(self):
        """
        Lists all available sensor types.
        Returns: list of sensor types.

        """
        sensor_types = []
        for sensor in self.sensors.entries.values():
            if sensor.instrument_type not in sensor_types:
                sensor_types.append(sensor.instrument_type)
        return sensor_types

    def list_sensors(self, sensor_type:str=None) -> list:
        """
        Lists all available sensors.
        Returns:

        """
        sensors = []
        for sensor in self.sensors.entries.values():
            if sensor_type is not None:
                if sensor.instrument_type == sensor_type:
                    sensors.append(sensor.sensor_name)
            else:
                sensors.append(sensor.sensor_name)
        return sensors

    def get_sensor_info(self,platform_type:str,sensor_type:str):
        """

        Returns:

        """
        for sensor in self.sensors.entries.values():
            if platform_type in sensor.platform_compatibility and sensor_type == sensor.instrument_type:
                return sensor

    def list_parameters(self):
        """
        Lists all available parameters.
        Returns:

        """
        parameters = []
        for parameter in self.parameters.entries.values():
            parameters.append(parameter.parameter_id)
        return parameters

    def list_parameter_aliases(self):
        """
        Lists all available parameter aliases.
        Returns:

        """
        parameter_aliases = {}
        for parameter in self.parameters.entries.values():
            parameter_aliases[parameter.parameter_id] = parameter.alternate_labels
        return parameter_aliases

    def get_parameter_info(self,parameter_ref:str):
        for parameter in self.parameters.entries.values():
            if parameter_ref == parameter.parameter_id or parameter_ref in parameter.alternate_labels:
                return parameter

    def create_platform_entity(self,entity_name: str, platform:str,serial_number:str,NMEA_conversion:bool=None):
        return self.platforms.create_entity(entity_name=entity_name, platform=platform,serial_number=serial_number,NMEA_conversion=NMEA_conversion)

inventory = InventoryClass()