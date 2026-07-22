import datetime as dt
from .esi_async import (ESICentroAPI, ATTR_DEVICE_ID, ATTR_DEVICE_IP, ATTR_DEVICE_MAC,
                        ATTR_DEVICE_NAME, ATTR_DEVICE_TYPE, ATTR_MEASURED_TEMPERATURE,
                        ATTR_TARGET_TEMPERATURE, ATTR_WORK_MODE, ATTR_TH_WORK)


class ESIDeviceError(Exception):
    """Base error for ESIDevice library."""


class ESIDeviceInitError(ESIDeviceError):
    """Raised when a device can't be initialised"""


class ESIDevice:
    """Represents a single ESI device."""

    def __init__(self, *, raw_data: dict, api: ESICentroAPI) -> None:
        """Initialise an ESI device from raw data."""
        self._api = api
        self._raw_data = raw_data
        self._last_update = dt.datetime.now()


    @property
    def last_update(self) -> dt.datetime:
        return self._last_update


    @property
    def device_id(self) -> str | None:
        if self._raw_data is None:
            return None
        return self._raw_data.get(ATTR_DEVICE_ID, None)


    @property
    def device_ip(self) -> str | None:
        if self._raw_data is None:
            return None
        return self._raw_data.get(ATTR_DEVICE_IP, None)


    @property
    def device_mac(self) -> str | None:
        if self._raw_data is None:
            return None
        return self._raw_data.get(ATTR_DEVICE_MAC, None)


    @property
    def device_name(self) -> str | None:
        if self._raw_data is None:
            return None
        return self._raw_data.get(ATTR_DEVICE_NAME, None)


    @property
    def device_type(self) -> str | None:
        if self._raw_data is None:
            return None
        return self._raw_data.get(ATTR_DEVICE_TYPE, None)


    # Measured temperature is what the API calls "current_temprature"
    # Although it goes against the recommendation from the HASS
    # "Python library: Modelling data" section, it is far easier
    # to deal with this as a float than a scaled string.
    @property
    def measured_temperature(self) -> float | None:
        if self._raw_data is None:
            return None
        temp = self._raw_data.get(ATTR_MEASURED_TEMPERATURE, None)
        if temp is not None:
            return float(temp)/10
        return None


    # Target temperature is what the API calls "inside_temparature"
    # Although it goes against the recommendation from the HASS
    # "Python library: Modelling data" section, it is far easier
    # to deal with this as a float than a scaled string.
    @property
    def target_temperature(self) -> float | None:
        if self._raw_data is None:
            return None
        temp = self._raw_data.get(ATTR_TARGET_TEMPERATURE, None)
        if temp is not None:
            return float(temp)/10
        return None


    # The meaning of work mode depends on the type of device,
    # it is different for a climate vs HW Cylinder stat.
    @property
    def work_mode(self) -> int | None:
        if self._raw_data is None:
            return None
        wm = self._raw_data.get(ATTR_WORK_MODE, None)
        if wm is not None:
            return int(wm)
        return None


    # th_work seems to be "0" for idle and "1" for actively heating
    @property
    def th_work(self) -> str | None:
        if self._raw_data is None:
            return None
        return self._raw_data.get(ATTR_TH_WORK, "0")


    # The value of work_mode depends on the type of the device
    # Temperature is a float with is the target temp in Celcius.
    async def async_set_work_mode(self, *, work_mode: int, temperature: float, message_id: int | None = None) -> None:
        """Set the work mode and temperature of this device."""
        if self.device_id is None:
            raise ValueError("Device ID is not available")
        await self._api.async_set_work_mode(device_id=self.device_id, work_mode=work_mode, temperature=temperature, message_id=message_id)


    async def async_update(self) -> None:
        """Update the device's data from the API."""
        await self._api.async_update_devices()
        if self.device_id is None:
            raise ValueError("Device ID is unknown")
        # Update the raw data for this device
        d = self._api.device_by_device_id(self.device_id)
        if d is not None:
            self._raw_data = d
            self._last_update = dt.datetime.now()
        