# esi-controls-async

## Introduction

Python API async client to the ESI Controls API for monitoring and controlling your thermostat.

This is mostly derived from Josh Taylor's [ESI_Controls] which is synchronous only, but there are also lessons learned from DeclanSC's [HASS_ESI_Thermostat] code.

The main motivation for writing this is to support my version of [HASS_ESI_Thermostat-jfd] which I intend to use to separate the protocol specific code from the integration, as described in [Building_a_Python_Library_for_an_API].

Apparently, the ESI Controls 'Centro' mobile app uses a superset of those requests used by this API to control the ESI devices via their server.

## ESICentroAPI Usage

The ESICentroAPI satisfies the needs of [Authentication], and because it is async, this API depends on being initialized with an aiohttp.ClientSession:

```Python
import aiohttp
from esi_controls_async import (ESICentroAPI, ATTR_DEVICE_ID)
async def esi_client() -> None:
    # E.g. No existing session, so create one.
    async with aiohttp.ClientSession() as session:
        api = ESICentroAPI(session=session)
```

With the resulting object, you can login to associate a user_id and token, which
will be used for the session. The user_id and token are long lived, but if they
do expire, you can log in again. The API doesn't store the email and password.

```Python
        await api.login(email=args.email, password=args.password)
```

Assuming authorization was successful, available will return true.

```Python
        if not api.available()
            raise SystemExit("Can't log in")
```

With the authorization complete, you can request that API's cache of devices is updated from the server:

```Python
        await api.async_update_devices(
            device_types_csv=device_types_csv,
            page_size=100,      # page_size doesn't seem to matter when there is only 1 device
        )

```

Once the update is complete, the number of devices found can be checked:

```Python
        if api.num_devices() == 0:
            print("No devices returned.")
            return
```

To retrieve the dict for first device. The most common attributes have constants associated with them. Also be careful about the spellings used by the protocol as some of them deviate from English in surprising ways:

```Python
        d = api.device_by_index(0)
        if d is not None:
            dev_id = d.get(ATTR_DEVICE_ID, "")
            print(f"id={dev_id})
```

Now to update the target temperature, or change work mode, you need that dev_id:

```Python
        work_mode = 0 # Auto on both climate and water heater.
        temperature = 19.5 # Target temperature in Celcius
        await api.async_set_work_mode(device_id=dev_id, work_mode=work_mode, temperature=temperature)
```

The known work modes for the Water Heater are:

* Auto: 0
* Off: 1
* Manual: 2
* Preset: 3 (but I haven't discovered how to use this)
* Auto, with temperature override: 4
* Boost: 5

The known work modes for the Climate controls are:

* Auto: 0
* Auto, with temperature override: 1
* Off: 4
* Manual: 5

I only have a Water Heater module [ESCTP5] and I mostly use either manual or off. For this device, valid temperatures are 25.0 to 65.0 in half degree increments.

To check whether the update took effect:

```Python
        await api.async_update_devices()
        # There is no guarantee that device index values won't be different each update,
        # especially if a device goes off-line, so use the dev_id now.
        d = api.device_by_device_id(dev_id)
        target_temp = float(d.get(ATTR_TARGET_TEMPERATURE, "250"))/10
        print(f"id={dev_id} temp={target_temp:.1f}")
```

## ESIDevice Usage

Additionally, there is a [Modelling data] class called ESIDevice.

```Python
        from esi_controls_async import ESIDevice
        ...
        dev=ESIDevice(raw_data = api.device_by_index(0), api = api)
```

There are properties to extact the various attributes:

```Python
    idle = d.th_work=="0"
    print(f"id={d.device_id!r}", f"name={d.device_name!r}", f"type={d.device_type!r}",
          f"measured={d.measured_temperature:.1f}", f"target={d.target_temperature:.1f}",
          f"work_mode={d.work_mode!r}", f"idle={idle}")
```

Also to set the work mode of a device and to update the state:

```Python
        await d.async_set_work_mode(work_mode=work_mode, temperature=temperature)
        # Allow some time to propagate status to the device
        await asyncio.sleep(5.0)
        await d.async_update()
```

[ESI_Controls]: <https://github.com/josh-taylor/esi/>
[ESCTP5]: <https://www.esicontrols.co.uk/product/wifi-programmable-cylinder-thermostat/>
[HASS_ESI_Thermostat]: <https://github.com/DeclanSC/hass-esi-thermostat>
[HASS_ESI_Thermostat-jfd]: <https://github.com/j-f-d/hass-esi-thermostat>
[Building_a_Python_Library_for_an_API]: <https://developers.home-assistant.io/docs/api_lib_index>
[Authentication]: <https://developers.home-assistant.io/docs/api_lib_auth>
[Modelling data]: <https://developers.home-assistant.io/docs/api_lib_data_models>
