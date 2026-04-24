"""Constants for the Xiaomi Miio IR integration."""

from __future__ import annotations

DOMAIN = "xiaomi_miio_ir"

CONF_SLOT = "slot"
CONF_MODEL = "model"
CONF_SOCKET_TIMEOUT = "socket_timeout"

DEFAULT_NAME = "Xiaomi Miio IR Remote"
DEFAULT_SLOT = 1
DEFAULT_TIMEOUT = 30
DEFAULT_SOCKET_TIMEOUT = 1

SERVICE_LEARN = "remote_learn_command"

KNOWN_IR_MODELS = {
    "KTBL02LM",
    "ktbl02lm",
    "chuangmi.ir.v2",
    "chuangmi.remote.v2",
    "chuangmi.remote.h102a03",
    "xiaomi.wifispeaker.l05g",
    "lumi.acpartner.mcn02",
}

MODEL_LABELS = {
    "KTBL02LM": "Mijia Universal Remote Controller",
    "ktbl02lm": "Mijia Universal Remote Controller",
    "chuangmi.ir.v2": "Mijia Universal Remote Controller",
    "chuangmi.remote.v2": "Mijia Universal Remote Controller",
    "chuangmi.remote.h102a03": "Mijia Universal Remote Controller",
    "lumi.acpartner.mcn02": "Xiaomi Mi Air Conditioning Companion 2",
}
