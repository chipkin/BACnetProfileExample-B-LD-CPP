# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - unreleased

The example is now **Profile-functional**: the Lighting Output does what
ANSI/ASHRAE 135-2024 cl. 12.54 says one does, over time, and Wire Tests prove it
against a Python Peer.

### Added

- **A Lighting Output engine** (`main.cpp` section 1b, real BACnet behaviour). A
  `fadeTo` puts `Present_Value` at the target at once while `Tracking_Value` moves
  to it in proportion to the fade time with `In_Progress` = `fadeActive`; `rampTo`
  moves at the ramp rate with `rampActive`; then `idle`, with `Tracking_Value`
  equal to `Present_Value`. Every operation of Table 12-67 is carried out:
  `stepUp` / `stepDown` / `stepOn` / `stepOff` (with their 100 % and 1.0 %
  clamps, ignored while off), `warn`, `warnRelinquish` and `warnOff` (blink, hold
  for `Egress_Time` with `Egress_Active` TRUE, then relinquish or write 0.0 %,
  with conditions (a)-(c)), `stop` (holds a fade at its `Tracking_Value`, cancels
  an egress timer), `restoreOn`, `defaultOn`, `toggleRestore`, `toggleDefault`.
  The halting rules of cl. 12.54.6.1 (a higher- or same-priority write halts a
  command in progress; a lower one does not), "not executed" when the command's
  priority is not in control, and the `Present_Value` special values -1.0 to -7.0
  of Table 12-65.
- **A lamp Simulation** (`main.cpp` section 1c, labelled): a simulated dimming
  driver follows `Tracking_Value`, prints a blink for a blink-warn, and - with the
  test-only environment variable `BLD_TEST_LAMP_BURNS_OUT=1` - burns out the first
  time it is switched on, so the example reports `Reliability` = `lampFailure`.
- **`Reliability`** (optional) on the Lighting Output: `lampFailure` from the
  lamp, which sets the FAULT flag of `Status_Flags`. **`Out_Of_Service`** is
  writable, and while it is TRUE `Reliability` is writable too (cl. 12.54.12).
- **Writable, range-checked** `Default_Fade_Time` (100-86400000 ms),
  `Default_Ramp_Rate` (0.1-100 %/s), `Default_Step_Increment` (0.1-100 %) and
  `Egress_Time`.
- **Wire Tests** for the Profile Function and both Failure Modes:
  `tests/fade_test.py`, `ramp_step_test.py`, `stop_priority_test.py`,
  `warn_test.py`, `failure_test.py`, sharing `tests/ld_setup.py` (which carries
  a `BACnetLightingCommand` encoder and a sampler proposed for `wiretest/` 0.7.0).
  Each check was shown to fail with its behaviour removed from `main.cpp`. The
  tests use UDP ports 48020-48029.

### Changed

- **The BACnet Surface is exactly the profile's set**: Device, Lighting Output 1
  "Jade", Network Port 1. Analog Input 1 "Bronze", Binary Input 1 "Emerald",
  Multi-state Input 1 "Hot Pink", Analog Output 1 "Chartreuse", Binary Output 1
  "Fuchsia" and Multi-state Output 1 "Indigo" - inherited from the B-ASC example,
  not part of a B-LD (Annex L.11.2) - are removed, with the arrow keys that nudged
  Analog Input 1.
- `Lighting_Command` is recorded only when accepted, and operation `none` (and
  any proprietary operation) is refused with PROPERTY / VALUE_OUT_OF_RANGE, as
  Table 12-67 requires. `Present_Value` writes between 0.0 and 1.0 % are clamped
  to 1.0 % (cl. 12.54.4).
- APP_VERSION 1.1.3 -> 1.2.0. README (scenario, what is real and what is
  Simulation, Verify, Wire Tests), TUTORIAL ("Add a second Lighting Output", the
  engine and the Simulation), AGENTS.md, PICS (objects, writable properties,
  regenerated objects block) and `tests/README.md` rewritten to match.
- The discovery Wire Test expects the three objects, and the runner's default
  port is 48020.

### Fixed

- **`Last_On_Value` and `Default_On_Value` were listed in `Property_List` but
  never served**, so they read `0.0` (the stack's silent default). They now read
  the last `Present_Value` >= 1.0 % (100.0 until the light has been on) and 100.0.
- Clause citations: "cl. 12.54.9" (Status_Flags) was cited for the
  `Lighting_Command` defaults and the required target-level in TUTORIAL and
  AGENTS.md; they are cl. 12.54.6 Table 12-66 and Table 12-67.

## [1.1.3] - unreleased

### Changed

- **Stack Pin moves to `6.x` @ `64b2cfac5` (6.0.23)** from `6.x` @ `abd4cee1`
  (6.0.21), per the series rule that a pin moves to the latest `6.x` whenever an
  example is updated. No `main.cpp` change was needed (only APP_VERSION 1.1.2 ->
  1.1.3 and a comment).
- **Protocol_Revision 24 -> 30** (the stack's default at the new pin).
- **Segmentation is now supported** (`segmented-both`), by the stack: its
  customer build compiles segmentation in from this pin (stack #2992).
  `docs/PICS.md` section 5 updated and the objects block regenerated.
- **`common/` 3.0.0 -> 3.3.0**, copied verbatim from B-SS-CPP `b640a81`. 3.1.0
  and 3.3.0 only add keys this example does not use; 3.2.0 sends a broadcast the
  stack hands over with no address instead of dropping it.
- README, TUTORIAL, AGENTS.md and PICS version lines: stack 6.0.23, `common/`
  3.3.0, Protocol_Revision 30. README profile table re-synced.
- **`common/` 3.3.0 -> 3.4.0**, copied verbatim from B-SS-CPP `5d78299`:
  `HelperSendMessage` now sends a broadcast the stack addresses to this device's
  own socket to the subnet broadcast, instead of unicasting it back to itself
  (stack #3933). No change in this example's Wire Test results.
- **`wiretest/` 0.5.0 -> 0.6.0**, copied verbatim from B-LS-CPP. Backward
  compatible: it adds codec helpers and the `peer`, `alarm`, `workstation` and
  `wait` modules this example does not use yet.
- **The discovery Wire Test retries its Who-Is once**, printing a visible
  `[RETRY]` line, when no I-Am comes back in 3 s. Who-Is is unconfirmed, so
  nothing else retries it, and the example's UDP receive can drop a datagram on
  Windows.

### Fixed

- **The docs no longer say the light fades.** The example has no fade engine:
  every Lighting_Command completes at once, `Tracking_Value` always equals
  `Present_Value`, and `In_Progress` is always `idle` (the code always said so).
  The README "Verify" steps said the console showed the light "fading over 3000
  ms" and implied a 3-second fade; they now say the level changes at once and the
  log line only names the fade time the example resolved. README, TUTORIAL,
  AGENTS.md and PICS say this plainly. A real fade engine is phase-2 work.

### Added

- **Wire Tests** (`tests/`, README "Wire Tests"): `tests/discovery_test.py`, the
  series' discovery test from B-SS-CPP `da3e96f` with this example's object list
  as its control. It does Who-Is, reads the Device's `Object_List`, then every
  object's `Property_List` and every listed property, and fails on any Error,
  Reject, Abort or silence. `tests/run_wire_tests.py` runs it; CI runs it on
  Linux after the smoke test. Result: 15/15 on Windows (STATIC) and Linux
  (SOURCE), 138 reads, all values.
- `wiretest/` 0.5.0, the series' shared Wiretest Harness, vendored verbatim from
  B-BBMD-CPP `75aedd8`.

## [1.1.2] - unreleased

### Changed

- **Device renamed from the series' colour placeholder "Rainbow" to "Chipkin
  Example B-LD"** so devices from different examples in the series are
  distinguishable from each other on the same BACnet network - every example
  previously announced the identical Object_Name "Rainbow", which made two
  examples on one subnet indistinguishable by name. Sub-object names (Analog
  Input 1 "Bronze", etc.) are unchanged - only the Device object's name
  changed. `docs/colour-table.md` (series root) updated to match. APP_VERSION
  bumped 1.1.1 -> 1.1.2.

## [Unreleased]

### Fixed

- **`Application_Software_Version` (12) and `Firmware_Revision` (44) were
  hardcoded and stale** - both served from separate `APPLICATION_SOFTWARE_VERSION`
  / `FIRMWARE_REVISION` constants pinned to the literal `"1.0.0"`, unrelated to
  `APP_VERSION` (already `1.1.0`+) or to the linked CAS BACnet Stack build.
  Fixed: `Application_Software_Version` now reads `APP_VERSION` directly (one
  source of truth, can't drift from `--version`'s own banner again).
  `Firmware_Revision` is now built at runtime from the CAS BACnet Stack's own
  `BACnetStack_GetAPIMajorVersion()`/`GetAPIMinorVersion()`/
  `GetAPIPatchVersion()`/`GetAPIBuildVersion()` (the same 4 calls
  `common/CASExampleHelper.cpp`'s `PrintVersion()` already uses for the startup
  banner), populated once right after `LoadBACnetFunctions()` succeeds, into a
  new `static std::string g_firmwareRevision`. The old `FIRMWARE_REVISION` and
  `APPLICATION_SOFTWARE_VERSION` constants are removed entirely. Same fix
  already applied to `BACnetProfileExample-B-SCHUB-CPP`; matched its shape
  here. `APP_VERSION` bumped to `1.1.1` per this series' standing rebuild
  convention. Verified with a real ReadProperty (bacpypes3) against the
  running device: `Application_Software_Version = "1.1.1"`,
  `Firmware_Revision = "6.0.21.0"` - both now match the actual running
  build instead of a hardcoded `"1.0.0"` string.

### Changed — README/TUTORIAL/PICS restructure, SOURCE-mode build

- **Split the README** into three documents, matching the shape already applied
  to `BACnetProfileExample-B-SS-CPP`: `README.md` now covers only this example
  (intro, BIBBs/services/objects, the two ways to drive a light, build, run,
  verify, footprint, series table, references); the long-form "extending the
  example" / "who serves what" / conformance-review material moved to the new
  `TUTORIAL.md`; and a new `docs/PICS.md` carries the ANSI/ASHRAE 135 Annex A
  conformance statement (product description, BIBBs, services, segmentation,
  object types, data link, device address binding, networking, character sets,
  the generated objects-and-properties table, references).
- **`docs/objects.json` gained a `Device` entry** (previously the generated
  tables omitted the Device object entirely). Regenerated
  `docs/PICS.md`'s objects-and-properties block
  (`python tools/gen-objects-properties.py BACnetProfileExample-B-LD-CPP`) -
  zero ⚠ rows.
- **Build switched from a prebuilt STATIC library to the adapter's default
  SOURCE mode**: `cmake -B build -S .` / `cmake --build build --config Release`
  now compiles the stack straight into the executable, with no
  `tools/build-stack-static.sh` pre-step and no `-DCAS_BACNET_STACK_LINK=STATIC`
  flag. `CMakeLists.txt`'s header comment, `AGENTS.md`, and
  `.github/workflows/release.yml` (link-mode assertion, metrics `link_mode`,
  no more static-library cache/build steps or matrix `lib:` entries, packaged
  artifact now includes `TUTORIAL.md` and `docs/PICS.md`) all updated to match.
  The v1.1.0 footprint numbers in the README were measured from a STATIC build;
  the table now says so and the next release refreshes them from the
  SOURCE-mode build.
- **`main.cpp`**: absorbed the README's old "Before you ship" per-field
  guidance into comments next to the `CHANGE ALL OF THIS BEFORE YOU SHIP`
  constants (in particular the `DEVICE_NAME`/`Object_Name`-uniqueness warning,
  and notes on `MODEL_NAME`, `DEVICE_DESCRIPTION`,
  `FIRMWARE_REVISION`/`APPLICATION_SOFTWARE_VERSION`). No behavioural change.
- **Documented a real, previously-unrecorded defect**: `Local_Date` and
  `Local_Time` are optional Device properties served by `GetPropertyDate` /
  `GetPropertyTime`, but neither is ever turned on with
  `BACnetStack_SetPropertyEnabled` - so `IsPropertyEnabled` never finds them
  enabled and a `ReadProperty` of either fails `unknown-property` before either
  callback is reached, contrary to this file's own v1.1.0 entry above claiming
  a successful wire test. See `TUTORIAL.md`'s "Known limitation" section and
  `docs/objects.json`'s Device note. Not fixed in this change (out of scope for
  a docs restructure); the missing `SetPropertyEnabled` calls are the fix.

## [1.1.0] - 2026-09-15

### Changed — 6.x re-pin, STATIC link, F-TIMESYNC fixes

- **Stack re-pinned to `6.x` @ `abd4cee1` (reports itself as 6.0.21)**, up from
  the stale `756371c1` (v5.3.4-634) this repo had drifted to.
- **Links the CAS BACnet Stack as a prebuilt STATIC library**
  (`CAS_BACNET_STACK_LINK=STATIC`, built by `tools/build-stack-static.sh`)
  instead of compiling the stack from `source/`. `CMakeLists.txt`, the README
  "Link mode" section and `AGENTS.md` now describe STATIC only.
- **`common/` synced verbatim to v2.1.0** from `BACnetProfileExample-B-SS-CPP`
  (not bumped further).
- **API changes at this pin, fixed:**
  - Every `CallbackGetProperty*` typedef (`Real`, `Enumerated`,
    `UnsignedInteger`, `CharacterString`, `Bool`, `OctetString` -
    `LightingCommand` was already known about) gained a trailing
    `uint32_t* errorCode` parameter. All six implementations updated;
    `errorCode` is deliberately left unset on every path (none of them has an
    error condition to report).
  - `BACnetStack_AddNetworkPortObjectWithNetworkNumber` renamed to
    `BACnetStack_AddNetworkPortObject` (identical parameters). One call site
    updated.
- **Local_Date / Local_Time are now actually served** (`GetPropertyDate` /
  `GetPropertyTime`, backed by a new `g_syncedDateTime`). Previously these two
  required Device properties were not served at all and a ReadProperty of
  either failed `value-not-initialized` - confirmed by wire test. `SetSystemTime`
  now stores the TimeSynchronization value into `g_syncedDateTime` instead of
  only printing it, so a subsequent Local_Date/Local_Time read genuinely
  reflects the last synced time (verified by wire test: sent
  `2026-09-15 12:34:56`, read back `Local_Date` = `2026-9-15`, `Local_Time` =
  `12:34:56.00`). `g_syncedDateTime` is seeded from the host clock at start-up
  so a read before any sync also succeeds.
- **UTCTimeSynchronization confirmed NOT accepted, by design and by wire test**:
  this example enables only `SERVICE_TIME_SYNCHRONIZATION` (the profile allows
  DM-TS-B *or* DM-UTC-B, not both). A UTCTimeSynchronization request against a
  running instance is rejected by the stack itself
  (`Services is not supported service=[9]`) before reaching the application.
- Tagged the `Lighting_Command` and `TimeSynchronization` callback sections
  `F-LIGHT` / `F-TIMESYNC` as this wave's canonical implementations for later
  series repos to copy.
- README/AGENTS.md: removed stale "requires the not-yet-landed PR #240 /
  pinned to a feature branch" framing (that PR landed long ago); added the
  generated `## Objects and properties` and `## The BACnet profile example
  series` sections and a `## Footprint` placeholder (filled at release).

## [1.0.0] - unreleased

> Not tagged yet: this repository has no tags at all. `release.yml` publishes binaries on a `v*.*.*`
> tag, so until that tag exists this section describes what is on the
> branch, not what shipped.

### Changed

- **Links the CAS BACnet Stack through the `CASBACnetStack::Adapter` CMake target
  instead of compiling its `source/*.cpp` into this project directly.** `main.cpp`
  and `common/CASExampleHelper.cpp` now include `CASBACnetStackAdapter.h` and call
  `LoadBACnetFunctions()` once at the top of `main()`; **every `BACnetStack_*` call
  site is unchanged** — the adapter exposes the same export names in every link
  mode. `CAS_BACNET_STACK_LINK` (`SOURCE` default, or `STATIC`/`DLL`) now picks the
  link mode, so switching is a CMake flag rather than a code change. See the
  README's new "Link modes" section.
  - Stack pinned to `6.x-TestTool` @ `756371c1`, which carries the adapter
    (cas-bacnet-stack PRs #267 and #268).
  - `common/` bumped to **v1.5.1** (see `common/CHANGELOG.md`), byte-identical to
    the other migrated examples. The `LoadBACnetFunctions()` requirement is a
    contract change shared by every example in the series.
  - Release CI now passes `-DCAS_BACNET_STACK_LINK=SOURCE` **explicitly** and
    asserts it back out of `CMakeCache.txt`, so a published artifact stays a
    single self-contained executable even if the CMake default ever moves.
  - README: added parallel-build guidance for the ~600-file first compile and
    refreshed the versions shown.

First release: a complete B-LD (Lighting Device) tutorial.

### Added

- `main.cpp` implementing the **B-LD** profile and nothing more. It is the
  [B-ASC](https://github.com/chipkin/BACnetProfileExample-B-ASC-CPP) example plus
  the object the profile exists for:
  - **DS-LO-B** — `Lighting Output 1` ("Jade"). Its `Present_Value` (REAL,
    0–100 %) is **commandable** through the same 16-slot `Priority_Array` the
    B-SA outputs use, with `Relinquish_Default` = 0.0 so an uncommanded light is
    off. Its **`Lighting_Command`** — the constructed `BACnetLightingCommand`
    SEQUENCE — is served and accepted through the stack's typed callbacks, so the
    application deals only in plain numbers and never encodes BACnet.
    (The profile allows "DS-BLO-B **or** DS-LO-B"; only one is required, so this
    example implements the Lighting Output — the dimmable one that carries
    `Lighting_Command`.)
  - **DM-TS-B** — TimeSynchronization, so a lighting system can align scheduled
    scenes.
  - **DS-RP-B / DS-WP-B / DM-DDB-B / DM-DOB-B / DM-DCC-B** — carried over from
    B-ASC unchanged (the series through-line rule: code demonstrating a shared
    BIBB is identical in every example that has it).
- All of the Lighting Output's **required** properties, several of which no other
  object in the series has: `Tracking_Value`, `In_Progress`, `Blink_Warn_Enable`,
  `Egress_Time` (**seconds**, unlike the fade/ramp times), `Egress_Active`,
  `Default_Fade_Time` (**milliseconds**), `Default_Ramp_Rate`,
  `Default_Step_Increment`, and `Lighting_Command_Default_Priority`.
- Value validation: a `Lighting_Command` with a `target-level` outside 0–100 % or
  a `priority` outside 1–16 is rejected with `value-out-of-range`.

### Notes

- **Requires a CAS BACnet Stack with the Lighting_Command adapters**
  ([PR #240](https://github.com/chipkin/cas-bacnet-stack/pull/240)). Before that
  change the customer DLL had no way to serve or accept a constructed property, so
  `Lighting_Command` — a **required** property of the object that defines this
  profile — could not be implemented at all: the read hit the stack's
  "Unsupported datatype for callbacks" path. The submodule is pinned to
  `56866997` on `feat/constructed-property-adapters-6x`; **re-pin to the merge
  commit on `6.x` once that PR lands.**
- The `use*` flag on each optional `Lighting_Command` field is load-bearing, not
  decoration: per cl. 12.54.9 a `fadeTo` that omits `fade-time` must fade over
  `Default_Fade_Time`, **not** snap instantly because the value happened to arrive
  as 0. `SetPropertyLightingCommand` resolves each omitted optional to this
  light's default for exactly that reason.
- This example has no dimming hardware behind it, so it completes every command
  instantly and honestly reports `In_Progress` = `idle` and `Egress_Active` =
  `false`. A real driver would report `fadeActive` / `rampActive` while its
  hardware moves. Operations with no visible effect here (`warn`, `stepOn`, …) are
  accepted, recorded, and logged as such rather than pretended.
- Deliberately **not** implemented, because B-LD does not require them:
  ReadPropertyMultiple, SubscribeCOV, alarms/events, scheduling, trending. A
  device that *supervises* other lights is a **B-LS** — a different profile.
- Verified against **CAS BACnet Stack 6.0.0.0** at **Protocol_Revision 24**. Built
  and run on Windows (MSVC 2022, C++17): the device starts, registers all nine
  objects, marks `Lighting_Command` writable, and broadcasts its I-Am.

[1.0.0]: https://github.com/chipkin/BACnetProfileExample-B-LD-CPP/commits/llm-auto-2026-july
