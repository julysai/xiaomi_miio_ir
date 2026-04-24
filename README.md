# Xiaomi Miio IR

Home Assistant custom integration for Xiaomi IR bridges that expose the raw `miIO.ir_*` protocol.

## Supported devices

### Confirmed working

- **Mijia Universal Remote Controller** (`KTBL02LM`)
- **Chuangmi IR Remote**: `chuangmi.ir.v2`
- **Chuangmi Universal Remote**: `chuangmi.remote.v2`
- **Xiaomi Mi Air Conditioning Companion 2**: `lumi.acpartner.mcn02`

### Likely compatible

- `chuangmi.remote.h102a03`

The integration works with devices that expose the raw `miIO.ir_learn`, `miIO.ir_read`, and `miIO.ir_play` commands.

## What it provides

- A **remote** entity for supported Xiaomi IR bridges
- `remote.send_command` for raw and Pronto Hex payloads
- Standard `remote.learn_command` support
- Backward-compatible `remote.remote_learn_command` with explicit slot selection
- Entity attributes for the last learned code, device, and command name
- UI configuration for the default learn timeout and miIO socket timeout

## Install

Copy `custom_components/xiaomi_miio_ir` into your Home Assistant config directory:

```text
config/
  custom_components/
    xiaomi_miio_ir/
```

Restart Home Assistant, then add **Xiaomi Miio IR** from **Settings -> Devices & Services -> Add Integration**.

## Configuration

The setup flow asks for:

- **Host**: IP address or hostname of the IR bridge
- **Token**: miIO token
- **Name**: optional entity name
- **Default learn timeout**: default timeout used by learning services
- **Default learn slot**: storage slot used by the custom slot-based learn service
- **miIO socket timeout**: per-request timeout used for each raw miIO call to the device

After setup, open **Settings -> Devices & Services -> Xiaomi Miio IR -> Configure** to change the default learn timeout and miIO socket timeout.

## Learning commands

### Standard Home Assistant flow

Use `remote.learn_command` when you want the integration to behave like a normal Home Assistant remote:

```yaml
service: remote.learn_command
target:
  entity_id: remote.xiaomi_miio_ir_remote
data:
  device: tv
  command:
    - power
```

If `timeout` is omitted, the integration uses the timeout configured in the integration UI. This uses the entity's configured default slot. When a code is captured, the integration:

- shows a persistent notification
- updates `last_learned_code`
- stores `last_learned_device`
- stores `last_learned_command`

### Slot-based custom service

Use the custom service when you need to control the device storage slot explicitly:

```yaml
service: remote.remote_learn_command
target:
  entity_id: remote.xiaomi_miio_ir_remote
data:
  slot: 30
```

If `timeout` is omitted here, the integration also uses the timeout configured in the integration UI.

## Sending commands

### Learned raw code

```yaml
service: remote.send_command
target:
  entity_id: remote.xiaomi_miio_ir_remote
data:
  command:
    - "raw:BASE64_IR_CODE:38400"
```

### Plain base64 payload

```yaml
service: remote.send_command
target:
  entity_id: remote.xiaomi_miio_ir_remote
data:
  command:
    - "BASE64_IR_CODE"
```

### Pronto Hex

Pronto Hex payloads are accepted directly:

```yaml
service: remote.send_command
target:
  entity_id: remote.xiaomi_miio_ir_remote
data:
  command:
    - "0000 006D 0022 0002 ..."
```

## Notes

- The integration defaults the miIO socket timeout to 1 second to cut the long initial wait on send and learn operations.
- `remote.learn_command` uses the configured default slot; use `remote.remote_learn_command` if you need per-call slot control.
