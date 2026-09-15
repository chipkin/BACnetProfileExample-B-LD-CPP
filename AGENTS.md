# AGENTS.md

Guidance for AI coding agents working in this repository. See
<https://agents.md/> for the format. Human contributors should read
[README.md](README.md) first.

## What this project is

A **tutorial** C++ example that implements the BACnet **B-LD (Lighting Device)**
profile using the CAS BACnet Stack. It is one of a series - one git repo per
BACnet profile. The top priority is that the code reads like a tutorial a customer
can learn from and copy-paste. Favour clarity over cleverness.

## Layout

This repository is self-contained:

- `main.cpp` - the example device.
- `common/` - the shared helper (vendored).
- `submodules/cas-bacnet-stack/` - the **CAS BACnet Stack** as a git submodule
  (private; compiled from source). After cloning, run
  `git submodule update --init --recursive`.

## Build

This example links the CAS BACnet Stack as a prebuilt **STATIC** library - build
the library once from the pinned submodule commit, then configure and build:

```bash
git submodule update --init --recursive   # once, if not cloned with --recursive
tools/build-stack-static.sh BACnetProfileExample-B-LD-CPP   # from the series root
cmake -B build -S . -DCAS_BACNET_STACK_LINK=STATIC
cmake --build build --config Release
```

The stack library build compiles the whole stack (~600 files) once and takes a
few minutes; the example itself then builds in seconds, and later incremental
rebuilds are fast. Use `-D CAS_STACK_DIR=...` only if your stack lives outside
the bundled submodule. The adapter also offers a SOURCE mode (compiles the
stack straight into the executable, no library build); this example builds and
ships STATIC only.

## Run

```bash
./build/BACnetExampleBLD [--port 47808] [--deviceID 389016]   # Linux/macOS
.\build\Release\BACnetExampleBLD.exe [--port 47808] [--deviceID 389016]   # Windows
```

Interactive keys: `h` help, `q` quit, up/down nudge Analog Input 1. The light is
commanded over BACnet, not from the keyboard.

## The stack pin is not optional here

This example **requires** a stack containing the `Lighting_Command` typed adapters
(`BACnetStack_RegisterCallbackGetPropertyLightingCommand` /
`...SetPropertyLightingCommand`), present at the pinned commit
(`submodules/cas-bacnet-stack` @ `abd4cee1`, `6.x`). Without them,
`Lighting_Command` - a **required** property of the object that *defines* this
profile - cannot be served at all: the customer DLL has no constructed-property
pathway and the read hits `Unsupported datatype for callbacks`.

Do not "fix" a build failure against an older pin by removing `Lighting_Command`;
that would make the example non-conformant. Re-pin forward instead.

## Conventions

- Device is named "Rainbow"; objects use the series' colour names (the Lighting
  Output is "Jade"); vendor id 389; device instance **389016**.
- Implement **only** what B-LD requires - DS-RP-B, DS-WP-B, DS-LO-B, DM-DDB-B,
  DM-DOB-B, DM-DCC-B, DM-TS-B - but expose **every required property** of each
  object for Protocol_Revision 24.
- The profile allows "DS-BLO-B **or** DS-LO-B" and "DM-TS-B **or** DM-UTC-B". Only
  one of each is required; this example implements the Lighting Output and local
  TimeSync. **Do not add the other** - that is not what a profile example is for.
- Do **not** add COV, alarms, scheduling, or trending. A device that *supervises*
  other lights is a B-LS - a different profile with its own example.
- The objects and the DS-WP-B / DM-DCC-B code are **identical to B-ASC** on
  purpose (the through-line rule: code demonstrating a shared BIBB is the same in
  every example that has it). If you change them here, they must change in every
  example that shares them - prefer not to.
- The Lighting Output's `Present_Value` is **commandable**: never serve it
  yourself. Serve the `Priority_Array` slots + `Relinquish_Default` and let the
  stack resolve it - exactly as for the Analog Output.
- **Never edit `common/` in this repo alone** - it is a vendored copy shared by
  every example, with its own version and changelog. To change it: edit, bump the
  version, add a changelog entry, then re-copy into every example repository.

## Lighting_Command: the two things to get right

1. **Never touch BACnet encoding.** `Lighting_Command` is a constructed SEQUENCE,
   but the application only ever deals in plain numbers - the stack assembles and
   decodes it. If you find yourself packing bytes, you are doing it wrong.

2. **The `use*` flags are load-bearing, not decoration.** On the Set side,
   `useFadeTime == false` means *the writer omitted fade-time*, and the
   accompanying `fadeTime` value is **meaningless**. Per cl. 12.54.9 you must then
   apply `Default_Fade_Time` - a `fadeTo` with no fade-time fades over the
   default, it does **not** snap instantly because the value arrived as 0. The
   same holds for ramp-rate, step-increment, and priority. Trusting the value
   without checking its flag is the bug this API shape exists to prevent.

Watch the units - they are inconsistent by spec: `Default_Fade_Time` and
`fade-time` are **milliseconds**; `Egress_Time` is **seconds**.

## How to verify a change

There are no unit tests; verification is behavioural:

1. Build, then run one instance on a clear UDP port. If any `AddObject` or the
   `SetPropertyWritable(Lighting_Command)` call failed, the process exits non-zero
   - that alone catches a stack pinned without the adapters.
2. With a BACnet client, **Who-Is** → confirm **I-Am** from device 389016.
3. **ReadProperty** every required property of every object; confirm
   `Protocol_Revision` is 24 and `Object_List` lists all nine objects. Pay
   attention to the Lighting Output's unusual ones: `Tracking_Value`,
   `In_Progress`, `Blink_Warn_Enable`, `Egress_Time`, `Egress_Active`,
   `Default_Fade_Time`, `Default_Ramp_Rate`, `Default_Step_Increment`,
   `Lighting_Command_Default_Priority`.
4. **WriteProperty** `Lighting_Command` = `{fadeTo, target-level 75.0, fade-time
   3000}`, then read `Present_Value` (75.0) and `Lighting_Command` (reads back).
5. **The regression that matters:** write `{fadeTo, target-level 50.0}` with **no
   fade-time** and confirm the log shows **3000 ms** (`Default_Fade_Time`), not 0.
6. Write `target-level` = 150.0 → confirm `value-out-of-range`.
7. Confirm services that are not enabled (e.g. ReadPropertyMultiple, SubscribeCOV)
   are rejected.

## Releasing

Bump `APP_VERSION` in `main.cpp` and add an entry to [CHANGELOG.md](CHANGELOG.md),
then tag `vX.Y.Z`. The GitHub Actions workflow builds and publishes the release.

## License

The example source code is dedicated to the public domain under
[CC0-1.0](LICENSE). The CAS BACnet Stack is a separate, commercially licensed
product and is not covered by that dedication.
