class AUVExists(Exception):
    pass

class PlatformExists(Exception):
    pass

class UnknownAUV(Exception):
    pass

class UnknownPlatform(Exception):
    pass

class UnknownSensor(Exception):
    pass

class UnknownParameter(Exception):
    pass

class UnknownModelField(Exception):
    pass

class MissionExists(Exception):
    pass

class UnknownSourceKey(Exception):
    pass

class ValidationFailure(Exception):
    pass

class NullDataException(Exception):
    pass

class InvalidPlatform(Exception):
    pass

class InvalidPlatformEntry(Exception):
    pass

class InvalidSensor(Exception):
    pass

class InvalidParameter(Exception):
    pass

class CriticalParameterMissing(Exception):
    pass

class InvalidSensorRate(Exception):
    pass

class InvalidSensorBehaviour(Exception):
    pass
class DataloggerNotFound(Exception):
    pass