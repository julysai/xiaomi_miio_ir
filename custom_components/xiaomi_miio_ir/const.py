"""Constants for the Xiaomi Miio IR integration."""

from __future__ import annotations

DOMAIN = "xiaomi_miio_ir"

CONF_SLOT = "slot"
CONF_MODEL = "model"

DEFAULT_NAME = "Xiaomi Miio IR Remote"
DEFAULT_SLOT = 1
DEFAULT_TIMEOUT = 30
MIIO_SOCKET_TIMEOUT = 2

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
    "KTBL02LM": "Xiaomi Universal IR Remote",
    "ktbl02lm": "Xiaomi Universal IR Remote",
    "chuangmi.ir.v2": "Xiaomi Universal IR Remote",
    "chuangmi.remote.v2": "Xiaomi Universal IR Remote",
    "chuangmi.remote.h102a03": "Xiaomi Universal IR Remote",
    "lumi.acpartner.mcn02": "Xiaomi Mi Air Conditioning Companion 2",
}
