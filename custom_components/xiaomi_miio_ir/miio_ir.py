"""Raw miIO IR protocol helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from miio import ChuangmiIr, Device, DeviceException

from .const import KNOWN_IR_MODELS, MIIO_SOCKET_TIMEOUT

DEFAULT_FREQUENCY = 38400
MAX_SLOT = 1000000


class UnsupportedDeviceError(RuntimeError):
    """Raised when the device does not expose the IR protocol."""


@dataclass(frozen=True, slots=True)
class XiaomiMiioIrInfo:
    """Minimal device metadata used by the integration."""

    model: str
    mac_address: str
    firmware_version: str | None
    hardware_version: str | None


class XiaomiMiioIrDevice:
    """Simple raw miIO IR client shared by supported devices."""

    pronto_re = re.compile(ChuangmiIr.PRONTO_RE.pattern, re.IGNORECASE)

    def __init__(self, host: str, token: str) -> None:
        """Initialize the raw miIO client."""
        self.host = host
        self._device = Device(host, token, timeout=MIIO_SOCKET_TIMEOUT)

    def info(self) -> XiaomiMiioIrInfo:
        """Return basic device info."""
        info = self._device.info()
        return XiaomiMiioIrInfo(
            model=info.model,
            mac_address=info.mac_address,
            firmware_version=getattr(info, "firmware_version", None),
            hardware_version=getattr(info, "hardware_version", None),
        )

    def read(self, slot: int = 1) -> dict[str, Any]:
        """Read a learned IR command from a storage slot."""
        self._validate_slot(slot)
        response = self._device.send("miIO.ir_read", {"key": str(slot)})
        if not isinstance(response, dict):
            raise DeviceException(f"Unexpected IR read response: {response!r}")
        return response

    def learn(self, slot: int = 1) -> Any:
        """Put the device into IR learning mode."""
        self._validate_slot(slot)
        return self._device.send("miIO.ir_learn", {"key": str(slot)})

    def supports_ir(self) -> bool:
        """Return whether the device exposes the miIO IR protocol."""
        try:
            response = self.read(1)
        except DeviceException:
            return False

        return "code" in response

    def ensure_supported(self, model: str | None = None) -> None:
        """Raise when the device does not look like an IR-capable miIO device."""
        if model in KNOWN_IR_MODELS or self.supports_ir():
            return

        raise UnsupportedDeviceError(
            f"Unsupported model '{model}'. The device does not expose the miIO IR protocol."
        )

    def play(self, command: str) -> Any:
        """Play a command in raw or pronto form."""
        raw_code, frequency, length = self._parse_command(command)
        payload: dict[str, Any] = {"freq": frequency, "code": raw_code}
        if length >= 0:
            payload["length"] = length

        return self._device.send("miIO.ir_play", payload)

    def _parse_command(self, command: str) -> tuple[str, int, int]:
        """Normalize a Home Assistant command string into miIO IR play fields."""
        if ":" not in command:
            if self.pronto_re.match(command):
                raw_code, frequency = ChuangmiIr.pronto_to_raw(command)
                return raw_code, frequency, -1

            return command, DEFAULT_FREQUENCY, -1

        command_type, payload, *command_args = command.split(":")
        if command_type not in {"raw", "pronto"}:
            raise ValueError(f"Unsupported command format '{command_type}'")

        try:
            parsed_args = [int(value) for value in command_args]
        except ValueError as ex:
            raise ValueError("Command arguments must be integers") from ex

        if command_type == "raw":
            frequency = parsed_args[0] if parsed_args else DEFAULT_FREQUENCY
            length = parsed_args[1] if len(parsed_args) > 1 else -1
            return payload, frequency, length

        repeats = parsed_args[0] if parsed_args else 1
        length = parsed_args[1] if len(parsed_args) > 1 else -1
        raw_code, frequency = ChuangmiIr.pronto_to_raw(payload, repeats)
        return raw_code, frequency, length

    @staticmethod
    def extract_code(response: dict[str, Any]) -> str | None:
        """Extract a learned command payload if present."""
        code = response.get("code")
        return code or None

    @staticmethod
    def is_learn_timeout(response: dict[str, Any]) -> bool:
        """Return whether the read response indicates learning timed out."""
        error = response.get("error")
        return (
            isinstance(error, dict)
            and error.get("message") == "learn timeout"
        )

    @staticmethod
    def _validate_slot(slot: int) -> None:
        """Validate an IR storage slot."""
        if slot < 1 or slot > MAX_SLOT:
            raise ValueError(f"Invalid storage slot '{slot}'")
