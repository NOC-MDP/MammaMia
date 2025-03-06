class AUVExists(Exception):
    pass

class PlatformExists(Exception):
    pass

class UnknownAUV(Exception):
    pass

class UnknownSensor(Exception):
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

class InvalidSensor(Exception):
    pass

class InvalidParameter(Exception):
    pass