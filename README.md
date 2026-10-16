# BACnet B-LD (Lighting Device) - C++ example

A minimal, copy-paste-friendly example showing how to implement the BACnet
**B-LD (Lighting Device)** device profile in C++ using the
[CAS BACnet Stack](https://store.chipkin.com/services/stacks/bacnet-stack).
It listens on **BACnet/IP (UDP 47808)**, answers **ReadProperty** and
**WriteProperty** requests, is discoverable via **Who-Is / I-Am**, and runs one
**Lighting Output** the way a luminaire does: a lighting system writes
`Lighting_Command` and the light **fades, ramps, steps and blink-warns** over
time - `Present_Value` is the target at once, `Tracking_Value` walks to it,
`In_Progress` says what is running - or writes `Present_Value` through the
16-slot `Priority_Array`. The lamp and dimming driver behind it are a
[Simulation](#the-lamp-simulation); everything BACnet does with them is real.

**[Download a prebuilt binary](https://github.com/chipkin/BACnetProfileExample-B-LD-CPP/releases)**
(Windows and Linux x64) - or build it yourself, see [Build](#build) below.

- **[TUTORIAL.md](TUTORIAL.md)** - how to extend this example and how to review
  it for conformance. Read it when you start turning this into your own device.
- **[docs/PICS.md](docs/PICS.md)** - the Protocol Implementation Conformance
  Statement: every object, every property, and who answers it.

> **Versions:** this document describes **example v1.2.0**, built and verified
> against **CAS BACnet Stack 6.0.23** (`6.x` @ `64b2cfac5`), at
> **Protocol_Revision 30**, with the vendored `common/` helper at **v3.4.0**.
> Running the example prints all three - if what it prints disagrees with this
> line, trust the program and check `CHANGELOG.md`.

> **Requires a stack with the Lighting_Command adapters**
> (`BACnetStack_RegisterCallbackGetPropertyLightingCommand` /
> `...SetPropertyLightingCommand`), present at this example's pinned commit. See
> [TUTORIAL.md](TUTORIAL.md#serving-a-constructed-composite-property).

## What this example supports

| Required BIBB | What it means | How this example does it |
|---|---|---|
| **DS-RP-B** | Execute ReadProperty | `SERVICE_READ_PROPERTY`; `GetProperty*` callbacks |
| **DS-WP-B** | Execute WriteProperty | `SERVICE_WRITE_PROPERTY`; `SetProperty*` callbacks |
| **DS-LO-B** | Implement the Lighting Output object type | `Lighting Output 1` ("Jade") - commandable `Present_Value`, every `Lighting_Command` operation of Table 12-67, run over time |
| **DM-DDB-B** | Answer Who-Is with I-Am | Handled by the stack; plus an unsolicited I-Am on start-up |
| **DM-DOB-B** | Answer Who-Has with I-Have | Handled by the stack |
| **DM-DCC-B** | Execute DeviceCommunicationControl | Password-gated accept/reject; the stack runs the state machine |
| **DM-TS-B** | Execute TimeSynchronization | `SERVICE_TIME_SYNCHRONIZATION` + `SetSystemTime` callback |

The profile says **"DS-BLO-B *or* DS-LO-B"** - a Binary Lighting Output would
satisfy it too. Only one is required, so this example implements one: the
**Lighting Output**, the dimmable one, because it is the richer of the two and the
one that carries `Lighting_Command`.

Likewise **"DM-TS-B *or* DM-UTC-B"** - this example does local TimeSync only.

**Deliberately NOT included** - a B-LD does not require them: ReadPropertyMultiple,
SubscribeCOV, alarms and events, scheduling, trending. A device that *supervises*
other lights - writing to them - is a **B-LS**, a different profile.

## The device this example creates

```
Device 389016  "Chipkin Example B-LD"   (Vendor 389 - Chipkin Automation Systems)
    │
    ├── Lighting Output 1     "Jade"        Present_Value  0.0     (REAL 0-100%; commandable + Lighting_Command)
    └── Network Port 1        "Vermilion"   the BACnet/IP port     (required on every device)
```

That is exactly the profile's set: ANSI/ASHRAE 135-2024 Annex L.11.2 says "A B-LD
is any device that implements Binary Lighting Output and/or Lighting Output
objects", and every device has a Device and a Network Port. (Up to v1.1.3 the
example also carried the B-ASC example's sensor and output objects; they are not
part of a B-LD and were removed in v1.2.0.)

## The scenario: a light that fades

What a B-LD is for, in one sentence: **it is a light that does what a lighting
system tells it to, the way clause 12.54 says a Lighting Output does it.** This
example does that against a Peer - any BACnet client: a lighting supervisor
(B-LS), a Schedule in a building controller, a wall-station gateway, or the
Python client in [`tests/`](tests/README.md):

1. The Peer writes `Lighting_Command` = `{fadeTo, target-level 80, fade-time 2000}`.
   `Present_Value` reads **80 at once** - it is the target (cl. 12.54.4) - and
   `Priority_Array[16]` holds it (`Lighting_Command_Default_Priority`).
2. For the next 2 seconds `Tracking_Value` - the level the lamp is actually being
   driven at (cl. 12.54.5) - climbs from 0 to 80 in proportion to the time, and
   `In_Progress` reads `fadeActive`. Then it reads `idle` and `Tracking_Value`
   equals `Present_Value`.
3. `rampTo` does the same at a fixed rate in percent per second; `stepUp` /
   `stepDown` / `stepOn` / `stepOff` move the level by `step-increment` at once;
   a command that omits fade-time, ramp-rate or step-increment uses
   `Default_Fade_Time` / `Default_Ramp_Rate` / `Default_Step_Increment`.
4. `stop` halts a fade part-way and **holds the level**: `Tracking_Value` is
   written to the command's slot and `In_Progress` goes `idle`.
5. **Priorities arbitrate.** An operator writing `Present_Value` at priority 8
   mid-fade halts the priority-16 fade (cl. 12.54.6.1); the halted fade's target
   stays in `Priority_Array[16]`, and when priority 8 is relinquished the light
   goes there at once. A fade written at a priority that is not in control is
   stored but not executed. A lower-priority write never disturbs a fade.
6. **End of the day** (cl. 12.54's own example, Figure 12-14): `warnRelinquish`
   blinks the lamp, holds the level for `Egress_Time` with `Egress_Active` TRUE,
   then relinquishes; `warnOff` writes 0.0% instead; `stop` cancels the egress
   timer. `Present_Value` special values -1.0 to -7.0 (Table 12-65) do the same
   for a client that cannot write a `BACnetLightingCommand` - a Schedule, say.
   `restoreOn`, `defaultOn` and the two toggles use `Last_On_Value` and
   `Default_On_Value`.
7. **Failure Mode - a bad command.** A command whose fade-time, ramp-rate,
   step-increment or target-level is out of range, operation `none`, a
   `Present_Value` outside 0-100 %, or a `Default_*` out of range is refused with
   **Error PROPERTY / VALUE_OUT_OF_RANGE** (cl. 12.54.6, 12.54.4, 12.54.16-18),
   and the light does not move.
8. **Failure Mode - a burnt-out lamp.** The light reports `Reliability` =
   `lampFailure`, and the stack sets the **FAULT** flag of `Status_Flags`
   (cl. 12.54.9, 12.54.11). BACnet keeps working: commands still drive
   `Present_Value` and `Tracking_Value`.

Every step is printed on the console as it happens.

### What is real and what is Simulation

**Real BACnet behaviour** - section 1b of [`main.cpp`](main.cpp), the Lighting
Output engine: `Tracking_Value`, `In_Progress`, `Egress_Active`, `Last_On_Value`,
every operation of Table 12-67, the halting rules of cl. 12.54.6.1 and the special
values of Table 12-65. It runs in the example's main loop because the CAS BACnet
Stack's customer interface hands a `Lighting_Command` to the application as plain
numbers and stops there - the stack's own lighting engine is part of its
test-tool interface, which a product does not ship. A real luminaire runs this
timing itself anyway: only it knows how its driver moves.

### The lamp Simulation

There is no lamp on a PC. A few lines in section 1c of `main.cpp` stand in for
one and its dimming driver - non-BACnet scaffolding, outside the BACnet Surface:

- the **driver output** follows `Tracking_Value`;
- a **blink-warn** prints `Simulation: the lamp blinks` (cl. 12.54.6.2 leaves the
  blink itself a local matter, and it "shall not be reflected in the priority
  array or the tracking value");
- the **lamp can burn out**. A test-only environment variable,
  `BLD_TEST_LAMP_BURNS_OUT=1`, makes it fail the first time it is switched on, so
  the Wire Tests can show the Failure Mode without a lamp to break. It is not a
  command-line option and changes nothing on the BACnet Surface.

To port the example to hardware, delete section 1c, drive your dimmer from the
engine's `trackingValue`, and set `g_lampFailed` from your driver's lamp-failure
detection. A client can also simulate a fault **over BACnet**, the standard way:
write `Out_Of_Service` = TRUE and `Reliability` becomes writable, "to allow
simulating specific conditions or for testing purposes" (cl. 12.54.12).

## Two ways to drive a light

The example serves both, because BACnet requires both:

**1. `Present_Value`** (REAL, 0-100 %) is **commandable** - the same 16-slot
`Priority_Array` + `Relinquish_Default` mechanism every commandable object uses.
Writing it jumps the light straight to a level (the object has no `Transition`
property, so cl. 12.54.19 says the transition is NONE). `Relinquish_Default` is `0.0`, so
an uncommanded light is off.

**2. `Lighting_Command`** is the interesting one, and it is what makes a light a
light rather than a generic analog output. It is a **constructed** value - a
`BACnetLightingCommand` SEQUENCE - carrying an **operation** plus the optional
parameters that operation needs:

| Field | Type | |
|---|---|---|
| `operation` | enum | **mandatory** - fadeTo, rampTo, stepUp, stepDown, stepOn, stepOff, warn, warnOff, warnRelinquish, stop, restoreOn, defaultOn, toggleRestore, toggleDefault |
| `target-level` | REAL 0-100 % | fadeTo / rampTo (required there) |
| `ramp-rate` | REAL 0.1-100 % / s | rampTo; else `Default_Ramp_Rate` |
| `step-increment` | REAL 0.1-100 % | the step operations; else `Default_Step_Increment` |
| `fade-time` | Unsigned 100-86400000 ms | fadeTo; else `Default_Fade_Time` |
| `priority` | Unsigned 1-16 | else `Lighting_Command_Default_Priority` (16) |

It tells the light **how** to get somewhere, not just where: *"fade to 75 % over
3 seconds"* rather than *"be 75 % now"* - and the example does it over the 3
seconds (see [the scenario](#the-scenario-a-light-that-fades)).

> **Which priority does a `Lighting_Command` command at?** Its **embedded**
> `priority` field - *not* the WriteProperty service priority you sent the request
> at. Write a `Lighting_Command` with no `priority` field and it lands at
> `Lighting_Command_Default_Priority` (16), even if the WriteProperty itself used
> priority 8. The two are unrelated: the service priority governs the write of the
> `Lighting_Command` property; the light's Priority_Array slot is chosen by the
> command's own field. (A direct `Present_Value` write, path #1, *does* use the
> WriteProperty service priority - that is the difference between the two paths.)

**The application never encodes or decodes that SEQUENCE.** It hands the stack the
fields as plain numbers through `RegisterCallbackGetPropertyLightingCommand` and
receives them the same way through `RegisterCallbackSetPropertyLightingCommand`.
There is no BACnet byte-twiddling anywhere in `main.cpp`. See
[TUTORIAL.md](TUTORIAL.md#serving-a-constructed-composite-property) for how.

## What's in this repository

This is a **self-contained** project. It ships:

- `main.cpp` - the example device.
- `common/` - the shared helper (UDP, callbacks, CLI, keyboard) vendored in.
- `CMakeLists.txt` - the build, the same on Windows, Linux, and macOS.
- `docs/PICS.md` - the conformance statement.
- `tests/` - the Wire Tests (see [Wire Tests](#wire-tests)), and `wiretest/`, the
  series' shared Python harness they are written against (vendored, like `common/`).
- `submodules/cas-bacnet-stack/` - the **CAS BACnet Stack as a git submodule**
  (private; requires a license - see below). Its sources are compiled into the
  executable, so there is no library or DLL to build, ship, or install.

## Requires the CAS BACnet Stack (licensed product)

This example **builds against the CAS BACnet Stack, which is a commercial Chipkin
product** - it is not free or open source, and there is no public/trial build.
The stack is referenced here as the **private** git submodule
`submodules/cas-bacnet-stack`; you can only fetch and build it once you have a CAS
BACnet Stack license and access to that repository.

**To get the CAS BACnet Stack (and access to build this example), contact
Chipkin:** <https://store.chipkin.com/services/stacks/bacnet-stack> or
sales@chipkin.com.

You do not need a stack licence to *read* this example, or to run a
[prebuilt release binary](https://github.com/chipkin/BACnetProfileExample-B-LD-CPP/releases).
The licence is what lets you *build* it - that is the part the stack submodule
gates.

## Prerequisites

- A C++17 compiler (MSVC, GCC, or Clang).
- CMake >= 3.15.
- Git (to fetch the stack submodule).

### Windows

- **C++ compiler** - install
  [Visual Studio Community](https://visualstudio.microsoft.com/downloads/)
  (free) and select the **"Desktop development with C++"** workload.
- **CMake** - from <https://cmake.org/download/>, or `winget install Kitware.CMake`.

### Linux / macOS

- Debian/Ubuntu: `sudo apt install build-essential cmake git`
- macOS: `xcode-select --install` and `brew install cmake`

## Build

CMake only, and the same two commands on every platform:

```bash
git clone --recursive https://github.com/chipkin/BACnetProfileExample-B-LD-CPP.git
cd BACnetProfileExample-B-LD-CPP

cmake -B build -S .
cmake --build build --config Release
```

Already cloned without `--recursive`? Run `git submodule update --init --recursive`
first - the build needs the stack submodule.

> **The first build takes a few minutes** - it compiles the entire CAS BACnet
> Stack (~600 source files) into the executable. Rebuilds after that are
> incremental and take seconds.

If your CAS BACnet Stack lives somewhere other than the bundled submodule, point
CMake at it: `cmake -B build -S . -D CAS_STACK_DIR=/path/to/cas-bacnet-stack`.

## Run

```bash
# Linux / macOS
./build/BACnetExampleBLD

# Windows
.\build\Release\BACnetExampleBLD.exe
```

Expected output:

```
BACnet B-LD (Lighting Device) Example - C++ v1.2.0
CAS BACnet Stack version: 6.0.23.0
Common helper (common/) version: 3.4.0
FYI: Listening for BACnet/IP on UDP port 47808 (Network Port 1).
TX 21 bytes to 192.168.3.255:47808 (broadcast) (Network Port 1) - Unconfirmed: I-Am
FYI: Device 389016 ("Chipkin Example B-LD") ready. Vendor ID 389. Press 'h' for help.
FYI: Lighting Output 1 (Jade) starts at 0.0% (off). WriteProperty its
     Lighting_Command to fade/ramp/step/warn it, or its Present_Value to set a level.
```

The `TX` line is the start-up I-Am the device broadcasts to announce itself. It
goes to the **local subnet broadcast** address (here `192.168.3.255`, computed
from the Network Port's interface), not the global `255.255.255.255`. As clients
talk to the device you'll see `RX ... bytes from ...` and `TX ... bytes to ...`
lines showing the traffic.

The device listens on UDP **47808** (BACnet/IP). Allow that port through your
firewall. To use a different port, pass `--port` (see below).

> **A wall of red `Error:` lines at start-up is expected and is not your bug** -
> it is the stack's own debug logging (the device hearing its own broadcast I-Am,
> and a one-time BACnet/SC UUID notice). [TUTORIAL.md](TUTORIAL.md#troubleshooting)
> explains both.

### Command-line options

| Option | Default | Meaning |
|--------|---------|---------|
| `--port <n>` | `47808` | UDP port to listen on (BACnet/IP). |
| `--deviceID <n>` | `389016` | The device's BACnet instance number (BACnet requires this to be configurable). |
| `--help`, `-h` | - | Show usage and exit. |
| `--version` | - | Print the example, stack, and `common/` helper versions, then exit. |

### Interactive commands

While the example runs, these keys are available:

| Key | Action |
|-----|--------|
| `h` | Show the version information and this command list. |
| `q` | Quit. |

The light is commanded over BACnet, not from the keyboard.

## Verify

Use a BACnet client such as the
[**CAS BACnet Explorer**](https://store.chipkin.com/products/tools/cas-bacnet-explorer):

1. **Discover** - send a **Who-Is**. The device replies with **I-Am** from
   instance **389016** (vendor **389**). It also broadcasts an I-Am at start-up.
2. **ReadProperty** `Lighting Output 1` `Present_Value` -> `0.0` (nothing has
   commanded it, so it rests at `Relinquish_Default` - the light is off).
3. **WriteProperty** `Lighting_Command` = `{operation: fadeTo, target-level: 75.0,
   fade-time: 3000}` -> the console logs `fadeTo 75.0% over 3000 ms`.
   `Present_Value` reads `75.0` straight away (the target); read `Tracking_Value`
   and `In_Progress` a few times in the next 3 seconds and watch the level climb
   with `In_Progress` = `fadeActive`, then `idle` at 75.
4. **ReadProperty** `Lighting_Command` -> the command you just sent, read back.
5. **WriteProperty** `Lighting_Command` = `{operation: fadeTo, target-level: 20.0}`
   - **no fade-time**. The console line names **3000 ms** (`Default_Fade_Time`),
   not 0, and the light takes 3 seconds to get there. That is the `use*` flag
   doing its job.
6. **WriteProperty** `Present_Value` = `50.0` at priority 8 while a fade runs ->
   the fade is halted and the light goes to 50 % directly; relinquish priority 8
   (write NULL) and it returns to the faded-to level at priority 16.
7. **TimeSynchronization** -> the console logs the time the device would set.

For a property-by-property review against the conformance statement, see
[TUTORIAL.md](TUTORIAL.md).

## Wire Tests

A Python BACnet client - the Peer - drives the running example over BACnet/IP
from outside it and proves the Profile Function: it writes `Lighting_Command` and
samples `Tracking_Value` / `In_Progress` every 0.1 s (monotonic, proportional to
the fade time, arrival on time), measures a ramp's rate, stops a fade part-way,
overrides it from a higher priority, runs a warn's egress time, and checks both
Failure Modes. Each behaviour was verified to make its check fail when removed
from `main.cpp`. Python 3 standard library only:

```bash
python3 tests/run_wire_tests.py --exe build/BACnetExampleBLD          # Linux/macOS
python tests\run_wire_tests.py --exe build\Release\BACnetExampleBLD.exe   # Windows
```

It ends with `ALL WIRE TESTS PASSED` (exit 0) after about a minute. CI runs it on
Linux after the smoke test. [tests/README.md](tests/README.md) says what each
check proves.

## The BACnet profile example series

<!-- PROFILE-TABLE:BEGIN (generated from cas-bacnet-stack-examples/docs/profile-table.md - do not edit here) -->
There is one example repository per standardized device profile in ASHRAE 135-2024 Annex L. An example marked ⛔ is blocked: the stack cannot yet perform that profile's function through its customer interface, and the example's README says what it does today. Pick the profile your device claims, then the language you build in. "Ask" means the example hasn't been built yet for that language - [contact Chipkin](https://store.chipkin.com/contact-us) if you need one.

### Controllers (Annex L.4)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-SS** Smart Sensor | [B-SS-CPP](https://github.com/chipkin/BACnetProfileExample-B-SS-CPP) | [B-SS-Node](https://github.com/chipkin/BACnetProfileExample-B-SS-Node) | [B-SS-CS](https://github.com/chipkin/BACnetProfileExample-B-SS-CS) | [B-SS-Rust](https://github.com/chipkin/BACnetProfileExample-B-SS-Rust) | [B-SS-Python](https://github.com/chipkin/BACnetProfileExample-B-SS-Python) | [B-SS-Go](https://github.com/chipkin/BACnetProfileExample-B-SS-Go) |
| **B-SA** Smart Actuator | [B-SA-CPP](https://github.com/chipkin/BACnetProfileExample-B-SA-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-ASC** Application Specific Controller | [B-ASC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ASC-CPP) | [B-ASC-Node](https://github.com/chipkin/BACnetProfileExample-B-ASC-Node) | Ask | Ask | Ask | Ask |
| **B-AAC** Advanced Application Controller | [B-AAC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AAC-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-BC** Building Controller | [B-BC-CPP](https://github.com/chipkin/BACnetProfileExample-B-BC-CPP) | Ask | Ask | Ask | Ask | Ask |

### Life safety controllers (Annex L.5)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-LSC** Life Safety Controller | [B-LSC-CPP](https://github.com/chipkin/BACnetProfileExample-B-LSC-CPP) 🚧 | Ask | Ask | Ask | Ask | Ask |
| **B-ALSC** Advanced Life Safety Controller | [B-ALSC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ALSC-CPP) | Ask | Ask | Ask | Ask | Ask |

### Access control controllers (Annex L.6)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-ACC** Access Control Controller | [B-ACC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACC-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-AACC** Advanced Access Control Controller | [B-AACC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AACC-CPP) | Ask | Ask | Ask | Ask | Ask |

### Lighting controllers (Annex L.11)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-LD** Lighting Device | [B-LD-CPP](https://github.com/chipkin/BACnetProfileExample-B-LD-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-LS** Lighting Supervisor | [B-LS-CPP](https://github.com/chipkin/BACnetProfileExample-B-LS-CPP) | Ask | Ask | Ask | Ask | Ask |

### Elevator controllers (Annex L.13)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-EM** Elevator Monitor | [B-EM-CPP](https://github.com/chipkin/BACnetProfileExample-B-EM-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-EC** Elevator Controller | [B-EC-CPP](https://github.com/chipkin/BACnetProfileExample-B-EC-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-AEC** Advanced Elevator Controller | [B-AEC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AEC-CPP) | Ask | Ask | Ask | Ask | Ask |

### Authentication and authorization (Annex L.14)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-AS** Authorization Server | [B-AS-CPP](https://github.com/chipkin/BACnetProfileExample-B-AS-CPP) ⛔ blocked on [stack #2043](https://github.com/chipkin/cas-bacnet-stack/issues/2043) | Ask | Ask | Ask | Ask | Ask |

### Miscellaneous (Annex L.7, combinable with any one family)

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-BBMD** Broadcast Management Device | [B-BBMD-CPP](https://github.com/chipkin/BACnetProfileExample-B-BBMD-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-ACDC** Access Control Door Controller | [B-ACDC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACDC-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-ACCR** Access Control Credential Reader | [B-ACCR-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACCR-CPP) ⛔ blocked on [stack #3934](https://github.com/chipkin/cas-bacnet-stack/issues/3934) | Ask | Ask | Ask | Ask | Ask |
| **B-RTR** Router | [B-RTR-CPP](https://github.com/chipkin/BACnetProfileExample-B-RTR-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-GW** Gateway | [B-GW-CPP](https://github.com/chipkin/BACnetProfileExample-B-GW-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-DAP** Device Address Proxy | [B-DAP-CPP](https://github.com/chipkin/BACnetProfileExample-B-DAP-CPP) ⛔ blocked on [stack #2032](https://github.com/chipkin/cas-bacnet-stack/issues/2032) | Ask | Ask | Ask | Ask | Ask |
| **B-SCHUB** BACnet/SC Hub | [B-SCHUB-CPP](https://github.com/chipkin/BACnetProfileExample-B-SCHUB-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-GENERAL** General device (Annex L.8) | *(satisfied by every example above)* | — | — | — | — | — |

### Operator interfaces and workstations (Annex L.1–L.3, L.9–L.10, L.12)

Client-side profiles.

| Profile | C++ | Node.js | C# | Rust | Python | Go |
|---|---|---|---|---|---|---|
| **B-OD** Operator Display | [B-OD-CPP](https://github.com/chipkin/BACnetProfileExample-B-OD-CPP) | Ask | Ask | Ask | Ask | Ask |
| **B-OWS** Operator Workstation | planned | — | — | — | — | — |
| **B-AWS** Advanced Operator Workstation | planned | — | — | — | — | — |
| **B-XAWS** Extended Advanced Operator Workstation | planned | — | — | — | — | — |
| **B-LSAP** Life Safety Annunciator Panel | planned | — | — | — | — | — |
| **B-LSWS** Life Safety Workstation | planned | — | — | — | — | — |
| **B-ALSWS** Advanced Life Safety Workstation | planned | — | — | — | — | — |
| **B-ACSD** Access Control Security Display | planned | — | — | — | — | — |
| **B-ACWS** Access Control Workstation | planned | — | — | — | — | — |
| **B-AACWS** Advanced Access Control Workstation | planned | — | — | — | — | — |
| **B-LOD** Lighting Operator Display | planned | — | — | — | — | — |
| **B-ALWS** Advanced Lighting Workstation | planned | — | — | — | — | — |
| **B-LCS** Lighting Control Station | planned | — | — | — | — | — |
| **B-ALCS** Advanced Lighting Control Station | planned | — | — | — | — | — |
| **B-ED** Elevator Display | planned | — | — | — | — | — |
| **B-EWS** Elevator Workstation | planned | — | — | — | — | — |
| **B-AEWS** Advanced Elevator Workstation | planned | — | — | — | — | — |

🚧 = in progress. ⛔ = Blocked Example (blocked on the named stack gap). "Ask" = not yet built for that language; contact Chipkin if you need it. Profile definitions: ANSI/ASHRAE 135-2024 Annex L. BIBB definitions: Annex K. Get the stack: <https://store.chipkin.com/services/stacks/bacnet-stack>.
<!-- PROFILE-TABLE:END -->

## References

- **ANSI/ASHRAE Standard 135** (BACnet) - the protocol standard. Object model
  (Clause 12), services (Clause 15), BACnet/IP (Annex J), device profiles
  (Annex L). Purchase / preview via the [ASHRAE store](https://www.ashrae.org/technical-resources/standards-and-guidelines).
- **What is BACnet?** - Chipkin's introduction:
  <https://docs.chipkin.com/protocols/bacnet/>.
- **CAS BACnet Stack** - product page and documentation:
  <https://store.chipkin.com/services/stacks/bacnet-stack>.
- **CAS BACnet Explorer** - client for testing this device:
  <https://store.chipkin.com/products/tools/cas-bacnet-explorer>.
- **Shared helper used by this example** - [`common/README.md`](common/README.md).

See also [TUTORIAL.md](TUTORIAL.md), [docs/PICS.md](docs/PICS.md),
[CHANGELOG.md](CHANGELOG.md), and [AGENTS.md](AGENTS.md).
