#!/usr/bin/env python3
from __future__ import annotations

import aiohttp, asyncio, argparse, sys
from typing import Any

sys.path.append("src/esi-controls-async")
from esi_async import (
    ATTR_TH_WORK,
    ESICentroAPI,
    ATTR_DEVICE_ID,
    ATTR_DEVICE_NAME,
    ATTR_DEVICE_TYPE,
    ATTR_MEASURED_TEMPERATURE,
    ATTR_TARGET_TEMPERATURE,
    ATTR_TH_WORK,
)


def prompt_int(prompt: str) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            return int(raw)
        except ValueError:
            print("Please enter a valid integer.")


def prompt_choice(prompt: str, mapping: dict[str, int]) -> int:
    keys = "/".join(mapping.keys())
    while True:
        raw = input(f"{prompt} ({keys}): ").strip().lower()
        if raw in mapping:
            return mapping[raw]
        print(f"Please enter one of: {keys}")


def parse_indices(raw: str) -> list[int]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [int(p) for p in parts]


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

    # These are correct for the water heater devices
    work_mode_waterheater = {"auto": 0, "off": 1, "manual": 2, "override": 4, "boost": 5}
    work_mode_climate = {"auto": 0, "override": 1, "off": 4, "manual": 5}

    async with aiohttp.ClientSession() as session:
        api = ESICentroAPI(session)
        await api.login(email=args.email, password=args.password)

        devices: dict[str, Any] = await api.async_list_devices(
            device_types_csv=device_types_csv,
            page_size=args.page_size,
        )

        if not devices:
            print("No devices returned.")
            return

        print("\nDiscovered devices:")
        for i, d in enumerate(devices.get("devices", [])):
            dev_id = str(d.get(ATTR_DEVICE_ID, ""))
            name = str(d.get(ATTR_DEVICE_NAME, ""))
            dtype = d.get(ATTR_DEVICE_TYPE, "")
            measured = float(d.get(ATTR_MEASURED_TEMPERATURE, "")) / 10.0
            target = float(d.get(ATTR_TARGET_TEMPERATURE, "")) / 10.0
            idle = d.get(ATTR_TH_WORK, "0") == "0"
            print(f"  [{i}] id={dev_id!r} name={name!r} type={dtype} measured={measured:.1f} target={target:.1f} idle={idle}")

        sel = input("\nSelect device index/indices (e.g. '0' or '0,2,3'): ").strip()
        indices = parse_indices(sel)

        chosen = []
        for idx in indices:
            if idx < 0 or idx >= len(devices.get("devices", [])):
                raise SystemExit(f"Index out of range: {idx}")
            chosen.append(devices.get("devices", [])[idx])

        if chosen and chosen[0].get(ATTR_DEVICE_TYPE) == "81":
            work_mode_map = work_mode_waterheater
            eg_temp = 55.0
        else:
            work_mode_map = work_mode_climate
            eg_temp = 20.0

        temperature = float(input(f"Enter target temperature (e.g. {eg_temp:.1f}): ")) * 10.0
        work_mode = prompt_choice("Enter work mode", work_mode_map)

        print("\nSending command...")
        for d in chosen:
            device_id = str(d.get(ATTR_DEVICE_ID, ""))
            print(f"  -> device_id={device_id} work_mode={work_mode} temperature={temperature:.0f}")
            await api.async_set_work_mode(device_id=device_id, work_mode=work_mode, temperature=int(temperature))

        print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
