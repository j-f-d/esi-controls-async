"""ESI Controls Async API exported interface"""

from aenum import Enum, unique

from .esi_async import *
from .esi_device import ESIDevice, ESIDeviceInitError


@unique
class ESIDeviceType(Enum): # type: ignore
    """Enumeration of device types."""

    RoomThermostat = 80
    HWThermostat = 81

@unique
class ESIRoomThermostatWorkMode(Enum): # type: ignore
    """Enumeration of climate work modes for the room thermostat.

    Values correspond to the device's reported work mode codes.
    """

    Auto = 0
    AutoOverride = 1
    AllDay = 2
    Boost = 3
    Off = 4
    Manual = 5
    Holiday = 6
    OffBoost = 7
    HolidayBoost = 8
    ManualBoost = 9

@unique
class ESIHWThermostatWorkMode(Enum): # type: ignore
    """Work mode for Hot Water Cylinder Thermostat devices.

    Values correspond to the device's reported work mode codes.
    """

    # The temperature is set based on a schedule, learned behavior, AI or some
    # other related mechanism. User is not able to adjust the temperature
    Auto = 0
    # All activity disabled / Device is off/standby
    Off = 1
    # Heating
    Manual = 2
    Preset = 3
    AutoOverride = 4
    Boost = 5

# TH_WORK seems to be one of two strings indicating idle or heating
@unique
class ESITHWork(Enum): # type: ignore
    Idle = 0
    Heating = 1

def device_type(ed : ESIDevice) -> ESIDeviceType | None:
    dev_type: ESIDeviceType | None = None
    device_type_str = ed.device_type
    if device_type_str is not None:
        try:
            dev_type = ESIDeviceType(int(device_type_str))
        except (ValueError, TypeError, AttributeError):
            # dev_type remains None
            pass
    return dev_type

__all__ = [
    # From esi_async.py
    "ESICentroAPI", "ESIDeviceListError",  "ESILoginError", "ESINoAuthorization", "ESISetCommandError",
    # From esi_device.py
    "ESIDevice", "ESIDeviceInitError",
    # From here
    "ESIDeviceType", "ESIHWThermostatWorkMode", "ESIRoomThermostatWorkMode", "ESITHWork", "device_type"
] 
