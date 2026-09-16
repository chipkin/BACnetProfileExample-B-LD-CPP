# BACnet B-LD (Lighting Device) - C++ example

A minimal, copy-paste-friendly example showing how to implement the BACnet
**B-LD (Lighting Device)** device profile in C++ using the
[CAS BACnet Stack](https://store.chipkin.com/services/stacks/bacnet-stack).
It listens on **BACnet/IP (UDP 47808)**, answers **ReadProperty** and
**WriteProperty** requests, is discoverable via **Who-Is / I-Am**, and drives a
commandable **Lighting Output** through both a `Priority_Array` and the
constructed `Lighting_Command` property.

**[Download a prebuilt binary](https://github.com/chipkin/BACnetProfileExample-B-LD-CPP/releases)**
(Windows and Linux x64) - or build it yourself, see [Build](#build) below.

- **[TUTORIAL.md](TUTORIAL.md)** - how to extend this example and how to review
  it for conformance. Read it when you start turning this into your own device.
- **[docs/PICS.md](docs/PICS.md)** - the Protocol Implementation Conformance
  Statement: every object, every property, and who answers it.

> **Versions:** this document describes **example v1.1.0**, built and verified
> against **CAS BACnet Stack 6.0.21** (`6.x` @ `abd4cee1`), at
> **Protocol_Revision 24**, with the vendored `common/` helper at **v2.5.0**.
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
| **DS-LO-B** | Present a Lighting Output | `Lighting Output 1` ("Jade") - commandable + `Lighting_Command` |
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
Device 389016  "Rainbow"   (Vendor 389 - Chipkin Automation Systems)
    │
    ├── Analog Input 1        "Bronze"      Present_Value  21.5    (REAL, degrees Celsius; read-only)
    ├── Binary Input 1        "Emerald"     Present_Value  active  (active / inactive; read-only)
    ├── Multi-State Input 1   "Hot Pink"    Present_Value  1       (state 1..3; read-only)
    ├── Analog Output 1       "Chartreuse"  Present_Value  20.0    (REAL setpoint; WRITABLE, commandable)
    ├── Binary Output 1       "Fuchsia"     Present_Value  inactive (WRITABLE, commandable)
    ├── Multi-State Output 1  "Indigo"      Present_Value  1       (state 1..3; WRITABLE, commandable)
    ├── Lighting Output 1     "Jade"        Present_Value  0.0     (REAL 0-100%; WRITABLE, commandable + Lighting_Command)
    └── Network Port 1        "Vermilion"   the BACnet/IP port     (required on every device)
```

## Two ways to drive a light

The example serves both, because BACnet requires both:

**1. `Present_Value`** (REAL, 0-100 %) is **commandable** - the same 16-slot
`Priority_Array` + `Relinquish_Default` mechanism the other output objects use.
Writing it jumps the light straight to a level. `Relinquish_Default` is `0.0`, so
an uncommanded light is off.

**2. `Lighting_Command`** is the interesting one, and it is what makes a light a
light rather than a generic analog output. It is a **constructed** value - a
`BACnetLightingCommand` SEQUENCE - carrying an **operation** plus the optional
parameters that operation needs:

| Field | Type | |
|---|---|---|
| `operation` | enum | **mandatory** - fadeTo, rampTo, stepUp, stepDown, warn, stop, ... |
| `target-level` | REAL 0-100 % | optional |
| `ramp-rate` | REAL % / s | optional |
| `step-increment` | REAL % | optional |
| `fade-time` | Unsigned ms | optional |
| `priority` | Unsigned 1-16 | optional |

It tells the light **how** to get somewhere, not just where: *"fade to 75 % over
3 seconds"* rather than *"be 75 % now"*.

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
BACnet B-LD (Lighting Device) Example - C++ v1.1.0
CAS BACnet Stack version: 6.0.21.0
Common helper (common/) version: 2.5.0
FYI: Listening for BACnet/IP on UDP port 47808 (Network Port 1).
TX 21 bytes to 192.168.3.255:47808 (broadcast) (Network Port 1)
FYI: Device 389016 ("Rainbow") ready. Vendor ID 389. Press 'h' for help.
FYI: Lighting Output 1 (Jade) starts at 0.0% (off). WriteProperty its
     Lighting_Command to fade/ramp/step it, or its Present_Value to set a level.
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
| up arrow | Increase Analog Input 1 (`Bronze`) by 1.1. |
| down arrow | Decrease Analog Input 1 (`Bronze`) by 1.1. |

The light is commanded over BACnet, not from the keyboard.

## Verify

Use a BACnet client such as the
[**CAS BACnet Explorer**](https://store.chipkin.com/products/tools/cas-bacnet-explorer):

1. **Discover** - send a **Who-Is**. The device replies with **I-Am** from
   instance **389016** (vendor **389**). It also broadcasts an I-Am at start-up.
2. **ReadProperty** `Lighting Output 1` `Present_Value` -> `0.0` (nothing has
   commanded it, so it rests at `Relinquish_Default` - the light is off).
3. **WriteProperty** `Lighting_Command` = `{operation: fadeTo, target-level: 75.0,
   fade-time: 3000}` -> the console logs the fade and `Present_Value` reads `75.0`.
4. **ReadProperty** `Lighting_Command` -> the command you just sent, read back.
5. **WriteProperty** `Lighting_Command` = `{operation: fadeTo, target-level: 50.0}`
   - **no fade-time**. The console shows it fading over **3000 ms**
   (`Default_Fade_Time`), not 0. That is the `use*` flag doing its job.
6. **WriteProperty** `Present_Value` = `20.0` at priority 8 -> the light goes to
   20 % directly, no fade. Both paths drive the same `Priority_Array`.
7. **TimeSynchronization** -> the console logs the time the device would set.

For a property-by-property review against the conformance statement, see
[TUTORIAL.md](TUTORIAL.md).


## The BACnet profile example series

<!-- PROFILE-TABLE:BEGIN (generated from cas-bacnet-stack-examples/docs/profile-table.md - do not edit here) -->
The CAS BACnet Stack supports every standardized device profile in ASHRAE 135-2024 Annex L, and there is one example repository per profile. Pick the profile your device claims, then the language you build in. "Ask" means the example hasn't been built yet for that language - [contact Chipkin](https://www.chipkin.com/contact/) if you need one.

### Controllers (Annex L.4)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-SS** Smart Sensor | [B-SS-CPP](https://github.com/chipkin/BACnetProfileExample-B-SS-CPP) | Ask | Ask | Ask | Ask |
| **B-SA** Smart Actuator | [B-SA-CPP](https://github.com/chipkin/BACnetProfileExample-B-SA-CPP) | Ask | Ask | Ask | Ask |
| **B-ASC** Application Specific Controller | [B-ASC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ASC-CPP) | [B-ASC-Node](https://github.com/chipkin/BACnetProfileExample-B-ASC-Node) | Ask | Ask | Ask |
| **B-AAC** Advanced Application Controller | [B-AAC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AAC-CPP) | Ask | Ask | Ask | Ask |
| **B-BC** Building Controller | [B-BC-CPP](https://github.com/chipkin/BACnetProfileExample-B-BC-CPP) | Ask | Ask | Ask | Ask |

### Life safety controllers (Annex L.5)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-LSC** Life Safety Controller | [B-LSC-CPP](https://github.com/chipkin/BACnetProfileExample-B-LSC-CPP) 🚧 | Ask | Ask | Ask | Ask |
| **B-ALSC** Advanced Life Safety Controller | [B-ALSC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ALSC-CPP) | Ask | Ask | Ask | Ask |

### Access control controllers (Annex L.6)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-ACC** Access Control Controller | [B-ACC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACC-CPP) | Ask | Ask | Ask | Ask |
| **B-AACC** Advanced Access Control Controller | [B-AACC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AACC-CPP) | Ask | Ask | Ask | Ask |

### Lighting controllers (Annex L.11)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-LD** Lighting Device | [B-LD-CPP](https://github.com/chipkin/BACnetProfileExample-B-LD-CPP) | Ask | Ask | Ask | Ask |
| **B-LS** Lighting Supervisor | [B-LS-CPP](https://github.com/chipkin/BACnetProfileExample-B-LS-CPP) | Ask | Ask | Ask | Ask |

### Elevator controllers (Annex L.13)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-EM** Elevator Monitor | [B-EM-CPP](https://github.com/chipkin/BACnetProfileExample-B-EM-CPP) | Ask | Ask | Ask | Ask |
| **B-EC** Elevator Controller | [B-EC-CPP](https://github.com/chipkin/BACnetProfileExample-B-EC-CPP) | Ask | Ask | Ask | Ask |
| **B-AEC** Advanced Elevator Controller | [B-AEC-CPP](https://github.com/chipkin/BACnetProfileExample-B-AEC-CPP) | Ask | Ask | Ask | Ask |

### Authentication and authorization (Annex L.14)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-AS** Authorization Server | [B-AS-CPP](https://github.com/chipkin/BACnetProfileExample-B-AS-CPP) | Ask | Ask | Ask | Ask |

### Miscellaneous (Annex L.7, combinable with any one family)

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-BBMD** Broadcast Management Device | [B-BBMD-CPP](https://github.com/chipkin/BACnetProfileExample-B-BBMD-CPP) | Ask | Ask | Ask | Ask |
| **B-ACDC** Access Control Door Controller | [B-ACDC-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACDC-CPP) | Ask | Ask | Ask | Ask |
| **B-ACCR** Access Control Credential Reader | [B-ACCR-CPP](https://github.com/chipkin/BACnetProfileExample-B-ACCR-CPP) | Ask | Ask | Ask | Ask |
| **B-RTR** Router | [B-RTR-CPP](https://github.com/chipkin/BACnetProfileExample-B-RTR-CPP) | Ask | Ask | Ask | Ask |
| **B-GW** Gateway | [B-GW-CPP](https://github.com/chipkin/BACnetProfileExample-B-GW-CPP) | Ask | Ask | Ask | Ask |
| **B-DAP** Device Address Proxy | [B-DAP-CPP](https://github.com/chipkin/BACnetProfileExample-B-DAP-CPP) | Ask | Ask | Ask | Ask |
| **B-SCHUB** BACnet/SC Hub | [B-SCHUB-CPP](https://github.com/chipkin/BACnetProfileExample-B-SCHUB-CPP) | Ask | Ask | Ask | Ask |
| **B-GENERAL** General device (Annex L.8) | *(satisfied by every example above)* | — | — | — | — |

### Operator interfaces and workstations (Annex L.1–L.3, L.9–L.10, L.12)

Client-side profiles.

| Profile | C++ | Node.js | C# | Rust | Python |
|---|---|---|---|---|---|
| **B-OD** Operator Display | [B-OD-CPP](https://github.com/chipkin/BACnetProfileExample-B-OD-CPP) | Ask | Ask | Ask | Ask |
| **B-OWS** Operator Workstation | planned | — | — | — | — |
| **B-AWS** Advanced Operator Workstation | planned | — | — | — | — |
| **B-XAWS** Extended Advanced Operator Workstation | planned | — | — | — | — |
| **B-LSAP** Life Safety Annunciator Panel | planned | — | — | — | — |
| **B-LSWS** Life Safety Workstation | planned | — | — | — | — |
| **B-ALSWS** Advanced Life Safety Workstation | planned | — | — | — | — |
| **B-ACSD** Access Control Security Display | planned | — | — | — | — |
| **B-ACWS** Access Control Workstation | planned | — | — | — | — |
| **B-AACWS** Advanced Access Control Workstation | planned | — | — | — | — |
| **B-LOD** Lighting Operator Display | planned | — | — | — | — |
| **B-ALWS** Advanced Lighting Workstation | planned | — | — | — | — |
| **B-LCS** Lighting Control Station | planned | — | — | — | — |
| **B-ALCS** Advanced Lighting Control Station | planned | — | — | — | — |
| **B-ED** Elevator Display | planned | — | — | — | — |
| **B-EWS** Elevator Workstation | planned | — | — | — | — |
| **B-AEWS** Advanced Elevator Workstation | planned | — | — | — | — |

🚧 = in progress. "Ask" = not yet built for that language; contact Chipkin if you need it. Profile definitions: ANSI/ASHRAE 135-2024 Annex L. BIBB definitions: Annex K. Get the stack: <https://store.chipkin.com/services/stacks/bacnet-stack>.
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
