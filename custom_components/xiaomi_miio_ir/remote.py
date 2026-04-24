"""Remote platform for Xiaomi Miio IR devices."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from functools import partial
import logging
from time import monotonic
from typing import Any

from miio import DeviceException
import voluptuous as vol

from homeassistant.components import persistent_notification
from homeassistant.components.remote import (
    ATTR_DELAY_SECS,
    ATTR_NUM_REPEATS,
    RemoteEntityFeature,
    DEFAULT_DELAY_SECS,
    RemoteEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TIMEOUT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_MODEL,
    CONF_SLOT,
    CONF_SOCKET_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_SOCKET_TIMEOUT,
    DEFAULT_SLOT,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MODEL_LABELS,
    SERVICE_LEARN,
)
from .miio_ir import UnsupportedDeviceError, XiaomiMiioIrDevice

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the Xiaomi Miio IR remote."""
    socket_timeout = entry.options.get(
        CONF_SOCKET_TIMEOUT,
        entry.data.get(CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT),
    )
    device = XiaomiMiioIrDevice(
        entry.data[CONF_HOST],
        entry.data[CONF_TOKEN],
        socket_timeout=socket_timeout,
    )

    try:
        info = await hass.async_add_executor_job(device.info)
        await hass.async_add_executor_job(device.ensure_supported, info.model)
    except (DeviceException, OSError, UnsupportedDeviceError) as ex:
        raise ConfigEntryNotReady(
            f"Failed to initialize Xiaomi Miio IR device at {entry.data[CONF_HOST]}"
        ) from ex

    unique_id = entry.unique_id or f"{info.model}-{info.mac_address}"
    model = entry.data.get(CONF_MODEL, info.model)
    friendly_name = entry.data.get(CONF_NAME) or MODEL_LABELS.get(model, DEFAULT_NAME)

    entity = XiaomiMiioIrRemote(
        hass=hass,
        device=device,
        host=entry.data[CONF_HOST],
        name=friendly_name,
        model=model,
        unique_id=unique_id,
        firmware_version=info.firmware_version,
        hardware_version=info.hardware_version,
        slot=entry.data.get(CONF_SLOT, DEFAULT_SLOT),
        timeout=entry.options.get(
            CONF_TIMEOUT, entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        ),
        socket_timeout=socket_timeout,
    )

    hass.data[DOMAIN][entry.entry_id]["entity"] = entity
    async_add_entities([entity])

    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service(
        SERVICE_LEARN,
        {
            vol.Optional(CONF_TIMEOUT): vol.All(int, vol.Range(min=1)),
            vol.Optional(CONF_SLOT): vol.All(int, vol.Range(min=1, max=1000000)),
        },
        "async_learn_command",
    )


class XiaomiMiioIrRemote(RemoteEntity):
    """Representation of a Xiaomi Miio IR remote."""

    _attr_should_poll = False
    _attr_supported_features = RemoteEntityFeature.LEARN_COMMAND

    def __init__(
        self,
        hass: HomeAssistant,
        device: XiaomiMiioIrDevice,
        host: str,
        name: str,
        model: str,
        unique_id: str,
        firmware_version: str | None,
        hardware_version: str | None,
        slot: int,
        timeout: int,
        socket_timeout: int,
    ) -> None:
        """Initialize the remote."""
        self.hass = hass
        self._device = device
        self._host = host
        self._model = model
        self._firmware_version = firmware_version
        self._hardware_version = hardware_version
        self._slot = slot
        self._timeout = timeout
        self._socket_timeout = socket_timeout
        self._last_learned_code: str | None = None
        self._last_learned_device: str | None = None
        self._last_learned_command: list[str] | None = None

        self._attr_name = name
        self._attr_unique_id = unique_id
        self._attr_available = True

    @property
    def is_on(self) -> bool:
        """The IR bridge is logically always on when reachable."""
        return self.available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        return {
            "host": self._host,
            "model": self._model,
            "default_slot": self._slot,
            "learn_timeout": self._timeout,
            "socket_timeout": self._socket_timeout,
            "last_learned_code": self._last_learned_code,
            "last_learned_device": self._last_learned_device,
            "last_learned_command": self._last_learned_command,
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device metadata for the registry."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "manufacturer": "Xiaomi",
            "model": self._model,
            "name": self.name,
            "sw_version": self._firmware_version,
            "hw_version": self._hardware_version,
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """IR remotes do not support turning on."""
        raise HomeAssistantError(
            "The Xiaomi Miio IR bridge cannot be turned on. Use remote.send_command instead."
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """IR remotes do not support turning off."""
        raise HomeAssistantError(
            "The Xiaomi Miio IR bridge cannot be turned off. Use remote.send_command instead."
        )

    async def async_send_command(
        self, command: Iterable[str] | str, **kwargs: Any
    ) -> None:
        """Send one or more IR commands."""
        commands = [command] if isinstance(command, str) else list(command)
        num_repeats = kwargs.get(ATTR_NUM_REPEATS, 1)
        delay = kwargs.get(ATTR_DELAY_SECS, DEFAULT_DELAY_SECS)

        for _ in range(num_repeats):
            for payload in commands:
                await self._async_device_call(self._device.play, payload)
                if delay:
                    await asyncio.sleep(delay)

    async def async_learn_command(
        self,
        *,
        device: str | None = None,
        command: Iterable[str] | None = None,
        timeout: int | None = None,
        slot: int | None = None,
        **kwargs: Any,
    ) -> None:
        """Learn an IR command and surface it through a persistent notification."""
        del kwargs
        if timeout is None:
            timeout = self._timeout
        if slot is None:
            slot = self._slot

        await self._async_device_call(self._device.learn, slot)

        started = monotonic()
        while monotonic() - started < timeout:
            response = await self._async_device_call(self._device.read, slot)
            code = self._device.extract_code(response)
            if code:
                self._last_learned_code = code
                self._last_learned_device = device
                self._last_learned_command = list(command) if command else None
                self.async_write_ha_state()

                detail_lines = [f"Learned IR command from {self.name} (slot {slot})"]
                if device:
                    detail_lines.append(f"Device: {device}")
                if command:
                    detail_lines.append(f"Command: {', '.join(command)}")

                message = "\n".join(detail_lines) + f"\n\n{code}"
                _LOGGER.warning(
                    "Learned IR command from %s slot %s: %s",
                    self.name,
                    slot,
                    code,
                )
                persistent_notification.async_create(
                    self.hass,
                    message,
                    title="Xiaomi Miio IR",
                    notification_id=f"{self.unique_id}-learned-ir",
                )
                return

            if self._device.is_learn_timeout(response):
                await self._async_device_call(self._device.learn, slot)

            await asyncio.sleep(1)

        persistent_notification.async_create(
            self.hass,
            f"Timed out waiting for an infrared command from {self.name} on slot {slot}.",
            title="Xiaomi Miio IR",
            notification_id=f"{self.unique_id}-learn-timeout",
        )
        raise HomeAssistantError("Timed out waiting for an infrared command")

    async def _async_device_call(self, method: Any, *args: Any) -> Any:
        """Run a miIO device call in the executor with availability tracking."""
        try:
            result = await self.hass.async_add_executor_job(partial(method, *args))
        except (DeviceException, OSError, ValueError) as ex:
            self._attr_available = False
            self.async_write_ha_state()
            raise HomeAssistantError(str(ex)) from ex

        self._attr_available = True
        return result
