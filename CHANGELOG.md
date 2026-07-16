# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - unreleased

> Not tagged yet: this repository has no tags at all. `release.yml` publishes binaries on a `v*.*.*`
> tag, so until that tag exists this section describes what is on the
> branch, not what shipped.

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
