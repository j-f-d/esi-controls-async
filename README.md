# esi-controls-async

## Introduction

Python API async client to the ESI Controls API for monitoring and controlling your thermostat.

This is somewhat inspired by Josh Taylor's [ESI_Controls] which is synchronous only.

## Usage

This API depends on being initialized with a aiohttp.ClientSession:

```Python
import aiohttp, esi_async
async def esi_client() -> None:
    # E.g. No existing session, so create one.
    async with aiohttp.ClientSession() as session:
        api = esi_async.ESICentroAPI(session)
```

With the object, you can login to associate a user_id and token, which
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

With the authorization complete, you can enumerate your devices:

```Python
        devices: dict[str, Any] = await api.async_list_devices(
            device_types_csv="1,2,4,10,20,23,25",
            page_size=4096,
        )
```

Now you can view the state of the devices from that dict, there's nothing
special about this, except that some expected attributes have constants
associated with them. Also be careful about the spellings used by the
protocol as some of them deviate from English in surprising ways.

```Python
        for i, d in enumerate(devices.get("devices", [])):
            dev_id = str(d.get(ATTR_DEVICE_ID, ""))
            name = str(d.get(ATTR_DEVICE_NAME, ""))
            dtype = d.get(ATTR_DEVICE_TYPE, "")
            measured = float(d.get(ATTR_MEASURED_TEMPERATURE, "")) / 10.0
            target = float(d.get(ATTR_TARGET_TEMPERATURE, "")) / 10.0
            print(f"  [{i}] id={dev_id!r} name={name!r} type={dtype} measured={measured:.1f} target={target:.1f}")
```

Now to update the target temperature, or change work mode, you need that dev_id:

```Python
        dev_id = str(devices.get("devices", [])[0].get(ATTR_DEVICE_ID, ""))
        work_mode = 0 # Auto on both climate and water heater.
        temperature = 195 # Actual temp * 10
        await api.async_set_work_mode(device_id=dev_id, work_mode=work_mode, temperature=temperature)
```

The known work modes for the Water Heater are:
    Auto: 0
    Off: 1
    Manual: 2
    Auto, with temperature override: 4
    Boost: 5

The known work modes for the Climate controls are:
    Auto: 0
    Auto, with temperature override: 1
    Off: 4
    Manual: 5

I only have a Water Heater module [ESCTP5] and I mostly use either manual or off. For this device, valid temperatures are 25.0 to 65.0 in half degree increments.

References:
[ESI_Controls]: https://github.com/josh-taylor/esi/
[ESCTP5]: https://www.esicontrols.co.uk/product/wifi-programmable-cylinder-thermostat/
