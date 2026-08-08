#!/usr/bin/env python3
import argparse
import asyncio
import sys
from typing import Any

import aiohttp

sys.path.append("src/esi-controls-async")
from esi_controls_async import (
    ESICentroAPI,
    ESIDevice,
    ESIDeviceType,
    ESIHWThermostatWorkMode,
    ESIRoomThermostatWorkMode,
    ESITHWork,
    device_type,
)


def prompt_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")


def prompt_choice(prompt: str, mapping: dict[str, Any]) -> int:
    keys = "/".join(mapping.keys())
    while True:
        raw = input(f"{prompt} ({keys}): ").strip()
        if raw in mapping:
            return mapping[raw]
        print(f"Please enter one of: {keys}")


def parse_indices(raw: str) -> list[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [int(p) for p in parts]


def print_device(ed : ESIDevice) -> None:
    idle = ed.th_work==str(ESITHWork.Idle)

    dev_type = device_type(ed)

    work_mode = ed.work_mode
    if work_mode is None:
        str_work_mode = "Unknown"
    else:
        match dev_type:
            case ESIDeviceType.RoomThermostat:
                str_work_mode = ESIRoomThermostatWorkMode(work_mode).name
            case ESIDeviceType.HWThermostat:
                str_work_mode = ESIHWThermostatWorkMode(work_mode).name
            case None | _:
                str_work_mode = str(work_mode)
    print(f"id={ed.device_id!r}", f"name={ed.device_name!r}", f"type={ed.device_type!r}",
          f"measured={ed.measured_temperature:.1f}", f"target={ed.target_temperature:.1f}",
          f"work_mode={str_work_mode!r}", f"idle={idle}")


async def main() -> None:

    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--device-types-csv", default="1,2,4,10,20,23,25")
    parser.add_argument("--page-size", type=int, default=100)
    args = parser.parse_args()

    device_types_csv = args.device_types_csv or input("Enter device_types_csv (e.g. '1' or '1,2'): ").strip()
    if not device_types_csv:
        raise SystemExit("device_types_csv cannot be empty.")

    async with aiohttp.ClientSession() as session:
        api = ESICentroAPI(session=session)
        await api.async_login(email=args.email, password=args.password)

        await api.async_update_devices(
            device_types_csv=device_types_csv,
            page_size=args.page_size,
        )

        if api.num_devices() == 0:
            print("No devices returned.")
            return

        found = []
        print("\nDiscovered devices:")
        for i in range(api.num_devices()):
            d = api.device_by_index(i)
            if d is None:
                continue
            ed = ESIDevice(api = api, raw_data = d)
            found.append(ed)
            print(f"  [{i}] ", end='')
            print_device(ed)

        sel = input("\nSelect device index/indices (e.g. '0' or '0,2,3'): ").strip() or "0"
        indices = parse_indices(sel)

        chosen = []
        for idx in indices:
            d = found[idx]
            if d is None:
                raise SystemExit(f"Index out of range: {idx}")
            chosen.append(d)

        if chosen and chosen[0].device_type == "81":
            work_mode_map = ESIHWThermostatWorkMode.__members__
            eg_temp = 55.0
        else:
            # There are more choices for Room Thermostats
            work_mode_map = ESIRoomThermostatWorkMode.__members__
            eg_temp = 20.0

        temperature = float(input(f"Enter target temperature in Celcius (e.g. {eg_temp:.1f}): ").strip() or str(eg_temp))
        work_mode = prompt_choice("Enter work mode", work_mode_map)

        print("\nSending command...")
        for d in chosen:
            print(f"  -> device_id={d.device_id} work_mode={d.work_mode} temperature={temperature:.1f}C")
            await d.async_set_work_mode(work_mode=int(work_mode), temperature=temperature)

        # Allow the update to propagate
        print("Waiting...")
        await asyncio.sleep(5.0)

        # This update is unnecessary because d.async_update calls async_update_devices()
        # await api.async_update_devices()

        print("\nChecking update success...")
        for d in chosen:
            await d.async_update()
            print_device(d)

        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
