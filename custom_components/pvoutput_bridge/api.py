"""Async client for the pvoutput.org API."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import logging

from aiohttp import ClientError, ClientSession

from .const import PVOUTPUT_BASE_URL

_LOGGER = logging.getLogger(__name__)


class PVOutputError(Exception):
    """Base exception for PVOutput API errors."""


class PVOutputAuthError(PVOutputError):
    """Raised when the API rejects the supplied credentials."""


class PVOutputRateLimitError(PVOutputError):
    """Raised when the PVOutput hourly rate limit has been exceeded."""


class PVOutputApiError(PVOutputError):
    """Raised for transport errors or other non-success PVOutput responses."""


@dataclass(slots=True)
class StatusPayload:
    """A single addstatus.jsp payload in Home Assistant-friendly units."""

    timestamp: datetime
    power_generation_w: float | None = None
    energy_generation_wh: float | None = None
    power_consumption_w: float | None = None
    energy_consumption_wh: float | None = None
    temperature_c: float | None = None
    voltage_v: float | None = None
    cumulative: bool = False
    net: bool = False

    def to_params(self) -> dict[str, str]:
        """Render the payload as PVOutput form parameters."""
        params: dict[str, str] = {
            "d": self.timestamp.strftime("%Y%m%d"),
            "t": self.timestamp.strftime("%H:%M"),
        }
        if self.energy_generation_wh is not None:
            params["v1"] = str(int(round(self.energy_generation_wh)))
        if self.power_generation_w is not None:
            params["v2"] = str(int(round(self.power_generation_w)))
        if self.energy_consumption_wh is not None:
            params["v3"] = str(int(round(self.energy_consumption_wh)))
        if self.power_consumption_w is not None:
            params["v4"] = str(int(round(self.power_consumption_w)))
        if self.temperature_c is not None:
            params["v5"] = f"{self.temperature_c:.1f}"
        if self.voltage_v is not None:
            params["v6"] = f"{self.voltage_v:.1f}"
        if self.cumulative:
            params["c1"] = "1"
        if self.net:
            params["n"] = "1"
        return params


@dataclass(slots=True)
class RateLimit:
    """PVOutput rate-limit state captured from response headers."""

    remaining: int | None = None
    limit: int | None = None
    reset: datetime | None = None


class PVOutputClient:
    """Async client for the PVOutput API."""

    def __init__(
        self,
        session: ClientSession,
        api_key: str,
        system_id: str,
        base_url: str = PVOUTPUT_BASE_URL,
    ) -> None:
        self._session = session
        self._api_key = api_key
        self._system_id = system_id
        self._base_url = base_url.rstrip("/")
        self.rate_limit = RateLimit()

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "X-Pvoutput-Apikey": self._api_key,
            "X-Pvoutput-SystemId": self._system_id,
        }

    async def async_validate_credentials(self) -> str:
        """Validate credentials via getsystem.jsp and return the system name."""
        body = await self._request("GET", "/getsystem.jsp")
        return body.split(",", 1)[0]

    async def async_add_status(self, payload: StatusPayload) -> None:
        """Upload a live status update via addstatus.jsp."""
        await self._request("POST", "/addstatus.jsp", data=payload.to_params())

    async def _request(
        self,
        method: str,
        path: str,
        *,
        data: Mapping[str, str] | None = None,
    ) -> str:
        url = f"{self._base_url}{path}"
        try:
            async with self._session.request(
                method,
                url,
                headers=self._headers,
                data=data,
            ) as response:
                self._update_rate_limit(response.headers)
                body = (await response.text()).strip()
                if response.status == 401:
                    raise PVOutputAuthError(body or "Unauthorized")
                if response.status == 403:
                    raise PVOutputRateLimitError(body or "Rate limit exceeded")
                if response.status >= 400:
                    raise PVOutputApiError(f"HTTP {response.status}: {body}")
                return body
        except ClientError as err:
            raise PVOutputApiError(f"Transport error: {err}") from err

    def _update_rate_limit(self, headers: Mapping[str, str]) -> None:
        remaining = headers.get("X-Rate-Limit-Remaining")
        limit = headers.get("X-Rate-Limit-Limit")
        reset = headers.get("X-Rate-Limit-Reset")
        try:
            self.rate_limit = RateLimit(
                remaining=int(remaining) if remaining is not None else None,
                limit=int(limit) if limit is not None else None,
                reset=(
                    datetime.fromtimestamp(int(reset), tz=UTC)
                    if reset is not None
                    else None
                ),
            )
        except (TypeError, ValueError):
            _LOGGER.debug("Could not parse PVOutput rate-limit headers")
