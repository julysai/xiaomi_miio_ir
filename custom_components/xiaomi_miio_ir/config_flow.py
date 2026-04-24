"""Config flow for the Xiaomi Miio IR integration."""

from __future__ import annotations

from typing import Any

from miio import DeviceException
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_TIMEOUT, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError

from .const import (
    CONF_MODEL,
    CONF_SEND_SOCKET_TIMEOUT,
    CONF_SLOT,
    CONF_SOCKET_TIMEOUT,
    DEFAULT_NAME,
    DEFAULT_SEND_SOCKET_TIMEOUT,
    DEFAULT_SLOT,
    DEFAULT_SOCKET_TIMEOUT,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from .miio_ir import UnsupportedDeviceError, XiaomiMiioIrDevice


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class UnsupportedModel(HomeAssistantError):
    """Error to indicate the device is not IR-capable."""


def _socket_timeout_schema() -> vol.All:
    """Build a socket timeout validator."""
    return vol.All(vol.Coerce(float), vol.Range(min=0.1))


def _user_schema(user_input: dict[str, Any] | None = None) -> vol.Schema:
    """Return the user step schema."""
    user_input = user_input or {}
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=user_input.get(CONF_HOST, "")): str,
            vol.Required(CONF_TOKEN, default=user_input.get(CONF_TOKEN, "")): str,
            vol.Optional(
                CONF_NAME,
                default=user_input.get(CONF_NAME, DEFAULT_NAME),
            ): str,
            vol.Optional(
                CONF_TIMEOUT,
                default=user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            ): vol.All(int, vol.Range(min=1)),
            vol.Optional(
                CONF_SLOT,
                default=user_input.get(CONF_SLOT, DEFAULT_SLOT),
            ): vol.All(int, vol.Range(min=1, max=1000000)),
            vol.Optional(
                CONF_SOCKET_TIMEOUT,
                default=user_input.get(CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT),
            ): _socket_timeout_schema(),
            vol.Optional(
                CONF_SEND_SOCKET_TIMEOUT,
                default=user_input.get(
                    CONF_SEND_SOCKET_TIMEOUT, DEFAULT_SEND_SOCKET_TIMEOUT
                ),
            ): _socket_timeout_schema(),
        }
    )


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate user input and return normalized device metadata."""
    device = XiaomiMiioIrDevice(
        data[CONF_HOST],
        data[CONF_TOKEN],
        socket_timeout=data.get(CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT),
    )

    try:
        info = await hass.async_add_executor_job(device.info)
        await hass.async_add_executor_job(device.ensure_supported, info.model)
    except UnsupportedDeviceError as ex:
        raise UnsupportedModel from ex
    except (DeviceException, OSError) as ex:
        raise CannotConnect from ex

    title = data.get(CONF_NAME) or f"{info.model} ({data[CONF_HOST]})"
    return {
        "title": title,
        "unique_id": f"{info.model}-{info.mac_address}",
        CONF_MODEL: info.model,
    }


class XiaomiMiioIrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Xiaomi Miio IR."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get the options flow for this handler."""
        return XiaomiMiioIrOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except UnsupportedModel:
                errors["base"] = "unsupported_model"
            except ValueError:
                errors["base"] = "invalid_config"
            else:
                await self.async_set_unique_id(info["unique_id"])
                self._abort_if_unique_id_configured(
                    updates={
                        CONF_HOST: user_input[CONF_HOST],
                        CONF_TOKEN: user_input[CONF_TOKEN],
                        CONF_NAME: user_input.get(CONF_NAME, DEFAULT_NAME),
                        CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                        CONF_SLOT: user_input.get(CONF_SLOT, DEFAULT_SLOT),
                        CONF_SOCKET_TIMEOUT: user_input.get(
                            CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT
                        ),
                        CONF_SEND_SOCKET_TIMEOUT: user_input.get(
                            CONF_SEND_SOCKET_TIMEOUT, DEFAULT_SEND_SOCKET_TIMEOUT
                        ),
                        CONF_MODEL: info[CONF_MODEL],
                    }
                )
                return self.async_create_entry(
                    title=info["title"],
                    data={
                        **user_input,
                        CONF_MODEL: info[CONF_MODEL],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input),
            errors=errors,
        )


class XiaomiMiioIrOptionsFlow(config_entries.OptionsFlowWithReload):
    """Handle Xiaomi Miio IR options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Manage Xiaomi Miio IR options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_timeout = self._config_entry.options.get(
            CONF_TIMEOUT,
            self._config_entry.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        )
        current_socket_timeout = self._config_entry.options.get(
            CONF_SOCKET_TIMEOUT,
            self._config_entry.data.get(
                CONF_SOCKET_TIMEOUT, DEFAULT_SOCKET_TIMEOUT
            ),
        )
        current_send_socket_timeout = self._config_entry.options.get(
            CONF_SEND_SOCKET_TIMEOUT,
            self._config_entry.data.get(
                CONF_SEND_SOCKET_TIMEOUT, DEFAULT_SEND_SOCKET_TIMEOUT
            ),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_TIMEOUT,
                        default=current_timeout,
                    ): vol.All(int, vol.Range(min=1)),
                    vol.Required(
                        CONF_SOCKET_TIMEOUT,
                        default=current_socket_timeout,
                    ): _socket_timeout_schema(),
                    vol.Required(
                        CONF_SEND_SOCKET_TIMEOUT,
                        default=current_send_socket_timeout,
                    ): _socket_timeout_schema(),
                }
            ),
        )
