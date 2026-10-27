# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No changes yet._

## [1.3.0] - 2026-10-27

Built on CAS BACnet Stack 6.x (69b6249f).

### Added

- **`--deviceName <text>`**: sets the Device's Object_Name at start-up, like
  `--deviceID` sets its instance. Object_Name must be unique on a BACnet
  internetwork, so two units no longer have to share the built-in name. The
  default is unchanged (`Chipkin Example B-LD`). A name must be 1 to 255 bytes
  with no control characters, otherwise the example warns and keeps the default.
  The name cannot be changed over the network.
- **Automated self-test** `tests/configuration_test.py` checks `--deviceID` and `--deviceName`.

### Changed

- **`--help` lists only the options the example reads.** It no longer lists
  `--dcc-password` (the password is `DCC_PASSWORD` in `main.cpp`). `--xml`, which
  was listed but did nothing, now prints each received and sent frame as XML.
- **`Local_Date` and `Local_Time` are documented as served** (the stack enables
  them together with TimeSynchronization).
- **Self-tests** default to UDP port 47830 (was 48020).
- **Documentation**: PICS lists Database_Revision as 3 (one per object added at
  start-up). The Lighting Output table gains `Property_List`,
  `Current_Command_Priority`, `Last_On_Value` and `Default_On_Value`, which the
  device already served. The Network Port no longer serves the optional
  `Reference_Port`, and `Number_Of_APDU_Retries` reads 3 (stack defaults).
- Vendored `common/` updated to 3.5.0 (see `common/CHANGELOG.md`).

### Fixed

- **Requests no longer go unanswered on Windows.** A request that arrived just as
  the socket's short receive timeout expired could be silently dropped. The
  receive loop now waits with `select()` (vendored `common/` 3.4.1).

## [1.2.0] - 2026-10-16

The Lighting Output now behaves as ANSI/ASHRAE 135-2024 cl. 12.54 describes, over
time, instead of completing every command at once. Built on CAS BACnet Stack 6.x
(64b2cfac5, reports 6.0.23).

### Added

- **Lighting Output engine.** A `fadeTo` sets `Present_Value` to the target at
  once while `Tracking_Value` moves to it over the fade time, with `In_Progress`
  = `fadeActive`; `rampTo` moves at the ramp rate (`rampActive`). All operations
  of Table 12-67 are carried out: `stepUp`, `stepDown`, `stepOn`, `stepOff`,
  `warn`, `warnRelinquish`, `warnOff` (blink, then hold for `Egress_Time` with
  `Egress_Active` TRUE), `stop`, `restoreOn`, `defaultOn`, `toggleRestore` and
  `toggleDefault`. A higher- or same-priority write halts a command in progress
  (cl. 12.54.6.1), and the `Present_Value` special values -1.0 to -7.0 are handled.
- **Simulated lamp.** A simulated dimming driver follows `Tracking_Value` and
  prints a blink for a blink-warn. Setting the environment variable
  `BLD_TEST_LAMP_BURNS_OUT=1` makes the lamp fail on first switch-on, so the
  example reports `Reliability` = `lampFailure`.
- **`Reliability`** (optional) on the Lighting Output; `lampFailure` sets the
  FAULT flag of `Status_Flags`. `Out_Of_Service` is writable, and while it is TRUE
  `Reliability` is writable too (cl. 12.54.12).
- **Writable, range-checked** `Default_Fade_Time` (100-86400000 ms),
  `Default_Ramp_Rate` (0.1-100 %/s), `Default_Step_Increment` (0.1-100 %) and
  `Egress_Time`.
- **Automated self-tests** under `tests/` for discovery, fade, ramp and step,
  stop and priority, warn, and lamp failure, using UDP ports 48020-48029.

### Changed

- **The device now serves only the profile's objects**: Device, Lighting Output 1
  "Jade" and Network Port 1. The Analog, Binary and Multi-state objects inherited
  from B-ASC are removed, with the arrow keys that changed Analog Input 1.
- **`Lighting_Command` is recorded only when accepted.** Operation `none` and
  proprietary operations are refused with VALUE_OUT_OF_RANGE (Table 12-67), and
  `Present_Value` writes between 0.0 and 1.0 % are raised to 1.0 % (cl. 12.54.4).
- **Protocol_Revision is 30** (docs said 24). Segmentation is supported in both
  directions, and the PICS says so.
- **Device renamed** from the placeholder "Rainbow" to "Chipkin Example B-LD", so
  examples in this series can be told apart on one network.
- **Documentation**: README is now this example only; configuration guidance and
  troubleshooting moved to a new `TUTORIAL.md`; a new `docs/PICS.md` lists the
  objects and properties.
- **Build**: the documented and released build compiles the stack from source
  with two commands (`cmake -B build -S .`, `cmake --build build --config Release`)
  on every platform. The prebuilt static library step is gone.
- Vendored `common/` updated to 3.4.0 (see `common/CHANGELOG.md`).
- `APP_VERSION` is 1.2.0.

### Fixed

- **`Last_On_Value` and `Default_On_Value` are now served.** They were listed in
  `Property_List` but read 0.0. They now read the last `Present_Value` of 1.0 %
  or more (100.0 until the light has been on) and 100.0.
- **`Application_Software_Version` and `Firmware_Revision`** now report the
  running build and linked stack version instead of a fixed "1.0.0".

## [1.1.0] - 2026-09-15

First tagged release: a B-LD (Lighting Device) example. It is the B-ASC example
plus a Lighting Output ("Jade") with a commandable `Present_Value`, a
`Lighting_Command` that is served and accepted, and all required Lighting Output
properties, plus TimeSynchronization. Built on CAS BACnet Stack 6.x (abd4cee1,
reports 6.0.21).

### Added

- **Lighting_Command** is accepted with range checks: a `target-level` outside
  0-100 % or a `priority` outside 1-16 is refused with VALUE_OUT_OF_RANGE.
- **TimeSynchronization** (DM-TS-B) is supported. `Local_Date` and `Local_Time`
  are served and reflect the last synchronized time. UTCTimeSynchronization is
  not accepted, because the profile allows one or the other.

### Changed

- The released build links a prebuilt static stack library
  (`tools/build-stack-static.sh`, `-DCAS_BACNET_STACK_LINK=STATIC`); see the
  README's "Link mode" section.
- Updated for the 6.0.21 stack API (callback signatures and the Network Port
  function name).
- Vendored `common/` updated to 2.1.0.
