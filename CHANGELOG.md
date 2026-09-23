# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
