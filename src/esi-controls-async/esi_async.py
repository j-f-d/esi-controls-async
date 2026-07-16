from __future__ import annotations

from abc import ABC
from aiohttp import ClientResponse, ClientSession, ClientTimeout
from dataclasses import dataclass
from typing import Any, Final

ESICENTRO_URL: Final = "https://esiheating.uksouth.cloudapp.azure.com/centro"
LOGIN_SUFFIX: Final = "/login"
DEVICE_LIST_SUFFIX: Final = "/getDeviceListNew"
SET_TEMP_SUFFIX: Final = "/setThermostatWorkModeNew"

# The device types with the exception of 1 are from https://github.com/josh-taylor/esi/blob/main/esi/esi.py
# Device type 1 is discovered by trial and error.
# These are used for the ATTR_DEVICE_TYPE parameter when fetching devices.
KNOWN_DEVICE_TYPES: Final = "1,2,4,10,20,23,25"

ATTR_DEVICE_ID: Final = "device_id"
ATTR_DEVICE_NAME: Final = "device_name"
ATTR_DEVICE_TYPE: Final = "device_type"

ATTR_MEASURED_TEMPERATURE: Final = "inside_temparature"   # bad protocol spelling
ATTR_TARGET_TEMPERATURE: Final = "current_temprature"    # bad protocol spelling

ATTR_WORK_MODE: Final = "work_mode"
ATTR_TH_WORK: Final = "th_work"


@dataclass
class ESIAuthorization:
    user_id: str
    token: str


class ESIProtocolError(Exception):
    """Base error for ESI protocol/library."""


class ESILoginError(ESIProtocolError):
    """Raised when login fails."""


class ESIDeviceListError(ESIProtocolError):
    """Raised when fetching device list fails."""


class ESISetCommandError(ESIProtocolError):
    """Raised when set command fails."""

class ESINoAuthorization(ESIProtocolError):
    """Raised when no authorization is available."""


class ESICentroAPI:
    """ESI protocol/library for login, fetch, and set-thermostat commands."""

    def __init__(
        self,
        session: ClientSession,
        host: str = ESICENTRO_URL
    ) -> None:
        self._session = session
        self._host = host
        self._auth: ESIAuthorization | None = None
        self._message_id = 1111

    def available(self) -> bool:
        """Check if this coordinator is available."""
        return self._auth is not None

    def next_message_id(self) -> str:
        self._message_id += 1
        return str(self._message_id)

    async def _json(self, response: ClientResponse) -> dict[str, Any]:
        """Local wrapper for JSON parsing function"""
        if response.status != 200:
            try:
                body = await response.text()
            except Exception:
                body = "<no body>"
            raise ESIProtocolError(f"API request failed: {response.status} body={body[:500]}")

        try:
            # Assume that whatever content type is reported it is valid for JSON parsing, by
            # setting the content_type parameter for json to the content-type header. If
            # the content-type header is missing, default to application/json.
            # This is necessary because, as of writing, the ESI API uses "text/json;utf-8"
            # instead of the RFC 4627 content-type of "application/json", which would cause
            # the JSON parser to fail.
            # This is a workaround for the ESI API not using the standard content-type and
            # could be removed if they change to match the RFC, but should still work if
            # they do.
            return await response.json(
                content_type=response.headers.get(
                    "content-type", "application/json"
                ).lower()
            )
        except Exception as err:
            try:
                body = await response.text()
            except Exception:
                body = "<no body>"
            raise ESIProtocolError(
                f"Response not recognised as JSON: {err}. "
                f"content-type={response.headers.get('content-type')} body={body[:500]}"
            ) from err

    async def login(self, *, email: str, password: str) -> None:
        payload = {"email": email, "password": password}

        async with self._session.post(
            self._host + LOGIN_SUFFIX,
            data=payload,
            timeout=ClientTimeout(total=15),
        ) as response:
            data = await self._json(response)

        if not data.get("statu") or not data.get("user", {}).get("token"):
            raise ESILoginError("Login failed")

        user_id = str(data["user"].get("id", ""))
        token = data["user"]["token"]
        self._auth = ESIAuthorization(user_id=user_id, token=token)

    async def async_list_devices(
        self,
        *,
        device_types_csv: str = KNOWN_DEVICE_TYPES,
        page_size: int = 100,
    ) -> dict[str, Any]:
        if self._auth is None:
            raise ESINoAuthorization("No authorization available")

        params = {
            "user_id": self._auth.user_id,
            "token": self._auth.token,
            ATTR_DEVICE_TYPE: device_types_csv,
            "pageSize": page_size,
        }

        async with self._session.post(
            self._host + DEVICE_LIST_SUFFIX,
            params=params,
            timeout=ClientTimeout(total=15),
        ) as response:
            data = await self._json(response)

        if not data.get("statu") or "devices" not in data:
            # Assume token is invalid and clear it so that we re-login next time
            self._auth = None
            raise ESIDeviceListError("Device list fetch failed")

        return {"devices": data["devices"]}

    async def async_set_work_mode(
        self,
        *,
        device_id: str,
        work_mode: int,
        temperature: int,
    ) -> None:
        if self._auth is None:
            raise ESINoAuthorization("No authorization available")

        params = {
            "user_id": self._auth.user_id,
            "token": self._auth.token,
            "messageId": self.next_message_id(),
            ATTR_DEVICE_ID: device_id,
            ATTR_WORK_MODE: str(work_mode),
            ATTR_TARGET_TEMPERATURE: temperature,
        }

        async with self._session.post(
            self._host + SET_TEMP_SUFFIX,
            params=params,
            timeout=ClientTimeout(total=5),
        ) as response:
            data = await self._json(response)

        if not data.get("statu"):
            error_msg = data.get("message", "Unknown error")
            error_code = data.get("error_code")

            if error_code is not None and int(error_code) == 7:
                raise ESISetCommandError(f"Work mode change rejected: {error_msg}")

            # Assume token is invalid and clear it so that we re-login next time
            self._auth = None
            raise ESISetCommandError(f"API error {error_code}: {error_msg}")
