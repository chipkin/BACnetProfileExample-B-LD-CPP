# BACnet B-LD (Lighting Device) — C++ example

A complete, self-contained C++ tutorial that implements the **B-LD (Lighting
Device)** profile from ASHRAE 135 Annex L using the
[CAS BACnet Stack](https://store.chipkin.com/products/stacks/cas-bacnet-stack).

Part of the CAS BACnet Stack **BACnet profile example series** — one repository
per BACnet device profile. This example claims **only** B-LD.

A **B-LD is a light**: a luminaire that a lighting system dims, fades, and
switches over BACnet. It is the
[B-ASC example](https://github.com/chipkin/BACnetProfileExample-B-ASC-CPP) plus a
Lighting Output object and time synchronisation.

> **Requires a stack with the Lighting_Command adapters** —
> [cas-bacnet-stack PR #240](https://github.com/chipkin/cas-bacnet-stack/pull/240).
> See [Why this example needs a recent stack](#why-this-example-needs-a-recent-stack).

## What this example supports

| Required BIBB | What it means | How this example does it |
|---|---|---|
| **DS-RP-B** | Execute ReadProperty | `SERVICE_READ_PROPERTY`; `GetProperty*` callbacks |
| **DS-WP-B** | Execute WriteProperty | `SERVICE_WRITE_PROPERTY`; `SetProperty*` callbacks |
| **DS-LO-B** | Present a Lighting Output | `Lighting Output 1` ("Jade") — commandable + `Lighting_Command` |
| **DM-DDB-B** | Answer Who-Is with I-Am | Handled by the stack; plus an unsolicited I-Am on start-up |
| **DM-DOB-B** | Answer Who-Has with I-Have | Handled by the stack |
| **DM-DCC-B** | Execute DeviceCommunicationControl | Identical to B-ASC |
| **DM-TS-B** | Execute TimeSynchronization | `SERVICE_TIME_SYNCHRONIZATION` + `SetSystemTime` callback |

The profile says **"DS-BLO-B *or* DS-LO-B"** — a Binary Lighting Output would
satisfy it too. Only one is required, so this example implements one: the
**Lighting Output**, the dimmable one, because it is the richer of the two and the
one that carries `Lighting_Command`.

Likewise **"DM-TS-B *or* DM-UTC-B"** — this example does local TimeSync.

**Deliberately NOT included** — a B-LD does not require them: ReadPropertyMultiple,
SubscribeCOV, alarms and events, scheduling, trending. A device that *supervises*
other lights — writing to them — is a **B-LS**, a different profile.

## Objects

| Object | Instance | Name | Notes |
|---|---|---|---|
| Device | 389016 | Rainbow | Configurable with `--deviceID` |
| Analog Input | 1 | Bronze | REAL, °C; read-only; starts at 21.5 |
| Binary Input | 1 | Emerald | active / inactive; read-only |
| Multi-State Input | 1 | Hot Pink | state 1..3; read-only |
| Analog Output | 1 | Chartreuse | REAL setpoint; WRITABLE, commandable |
| Binary Output | 1 | Fuchsia | active / inactive; WRITABLE, commandable |
| Multi-State Output | 1 | Indigo | state 1..3; WRITABLE, commandable |
| **Lighting Output** | **1** | **Jade** | **REAL 0–100 %; commandable + `Lighting_Command`** |
| Network Port | 1 | Vermilion | The BACnet/IP port (required) |

## Two ways to drive a light

The example serves both, because BACnet requires both:

**1. `Present_Value`** (REAL, 0–100 %) is **commandable** — the same 16-slot
`Priority_Array` + `Relinquish_Default` mechanism the
[B-SA](https://github.com/chipkin/BACnetProfileExample-B-SA-CPP) outputs use.
Writing it jumps the light straight to a level. `Relinquish_Default` is `0.0`, so
an uncommanded light is off.

**2. `Lighting_Command`** is the interesting one, and it is what makes a light a
light rather than a generic analog output. It is a **constructed** value — a
`BACnetLightingCommand` SEQUENCE — carrying an **operation** plus the optional
parameters that operation needs:

| Field | Type | |
|---|---|---|
| `operation` | enum | **mandatory** — fadeTo, rampTo, stepUp, stepDown, warn, stop, … |
| `target-level` | REAL 0–100 % | optional |
| `ramp-rate` | REAL % / s | optional |
| `step-increment` | REAL % | optional |
| `fade-time` | Unsigned ms | optional |
| `priority` | Unsigned 1–16 | optional |

It tells the light **how** to get somewhere, not just where: *"fade to 75 % over
3 seconds"* rather than *"be 75 % now"*.

> **Which priority does a `Lighting_Command` command at?** Its **embedded**
> `priority` field — *not* the WriteProperty service priority you sent the request
> at. Write a `Lighting_Command` with no `priority` field and it lands at
> `Lighting_Command_Default_Priority` (16), even if the WriteProperty itself used
> priority 8. The two are unrelated: the service priority governs the write of the
> `Lighting_Command` property; the light's Priority_Array slot is chosen by the
> command's own field. (A direct `Present_Value` write, path #1, *does* use the
> WriteProperty service priority — that is the difference between the two paths.)

**The application never encodes or decodes that SEQUENCE.** It hands the stack the
fields as plain numbers through `RegisterCallbackGetPropertyLightingCommand` and
receives them the same way through `RegisterCallbackSetPropertyLightingCommand`.
There is no BACnet byte-twiddling anywhere in `main.cpp`.

### The `use*` flags are load-bearing

Each optional field has a `use*` flag. On the **get** side, `false` omits the field
from the SEQUENCE. On the **set** side, `false` means **the writer omitted it** —
and the accompanying value is meaningless.

That distinction is the whole reason the flags exist. Per cl. 12.54.9, a `fadeTo`
with **no** `fade-time` means *"fade over `Default_Fade_Time`"* — **not** *"fade in
0 ms"*, which is what you would get if you naively trusted the value. This example
resolves each omitted optional to the light's own default for exactly that reason.

## A Lighting Output's required properties

Several exist on no other object in this series. Watch the units — they are not
consistent, and that is per spec:

| Property | Value here | Notes |
|---|---|---|
| `Tracking_Value` | live | What the light **is**, vs `Present_Value` = what it was **told** to be |
| `In_Progress` | `idle` | `fadeActive` / `rampActive` on real hardware mid-move |
| `Blink_Warn_Enable` | `true` | The "lights are about to go out" flash |
| `Egress_Time` | 30 | **seconds** |
| `Egress_Active` | `false` | True only while the egress timer runs |
| `Default_Fade_Time` | 3000 | **milliseconds** |
| `Default_Ramp_Rate` | 10.0 | % per second |
| `Default_Step_Increment` | 5.0 | % |
| `Lighting_Command_Default_Priority` | 16 | Priority a `Lighting_Command` writes at when it names none |

## Who serves what: application or stack?

The most common question reading `main.cpp` is "who answers this property?" For the
Lighting Output "Jade":

| Property | Served by | How |
|---|---|---|
| `Object_Identifier`, `Object_Type`, `Object_List`, `Property_List`, `Status_Flags` | **stack** | generated from the object you added |
| `Current_Command_Priority` | **stack** | computed from the Priority_Array (required at Protocol_Revision 24) |
| `Event_State` | **stack**, sort of | no alarming here, so it reads its datatype default `normal(0)` by coincidence, not computation |
| `Present_Value` | **you (write) / stack (read)** | `SetPropertyReal` accepts a direct write of the REAL level (0-100%); on read the **stack computes** Present_Value from the Priority_Array slots that `GetPropertyReal` serves (highest non-null slot, or Relinquish_Default) |
| `Object_Name` | **you** | `GetPropertyCharString` |
| the required lighting properties above (`Tracking_Value`, `In_Progress`, `Egress_Time`, `Default_Fade_Time`, ...) | **you** | typed Get callbacks (REAL / Enumerated / Unsigned / Bool) |
| **`Lighting_Command`** | **you, via a constructed-property adapter** | `GetPropertyLightingCommand` / `SetPropertyLightingCommand` - see below |

Note there is **no `Units`** row: a Lighting Output has no Units property (its level
is a dimensionless percent), so serving one would be dead code the stack never calls.

### Serving a constructed (composite) property

`Lighting_Command` is a **constructed** BACnet datatype - a SEQUENCE of an operation
plus several optional fields - not a primitive like REAL or Enumerated. A plain typed
callback (`GetPropertyReal`, `GetPropertyEnumerated`, ...) cannot serve it; the stack
would answer *unsupported-datatype*. Instead you register a **dedicated adapter
callback** for that property type (added to the CAS BACnet Stack in
[PR #240](https://github.com/chipkin/cas-bacnet-stack/pull/240)):

```cpp
// Register the Lighting_Command adapter callbacks (not the generic typed ones):
BACnetStack_RegisterCallbackGetPropertyLightingCommand(GetPropertyLightingCommand);
BACnetStack_RegisterCallbackSetPropertyLightingCommand(SetPropertyLightingCommand);
```

Your callback then works in the stack's **decoded field struct**, not raw bytes -
`GetPropertyLightingCommand` fills an operation + `use*` flags + values, and the
stack encodes the SEQUENCE on the wire. There is no BACnet byte-twiddling anywhere in
`main.cpp`. The `use*` flags are load-bearing: an omitted optional (e.g. a `fadeTo`
with no fade-time) must be left `use*=false` so the stack/light resolves it to the
object's default, rather than forced to a literal `0`. This is the pattern for **any**
constructed property (`BACnetDateTime`, `BACnetLightingCommand`, ...): a typed adapter
that speaks the decoded struct, never the wire bytes.

## Why this example needs a recent stack

`Lighting_Command` is a **required** property of the object that **defines** this
profile — and it is constructed. Until
[PR #240](https://github.com/chipkin/cas-bacnet-stack/pull/240), the customer-facing
DLL had **no way to serve or accept a constructed property at all**: the read hit
the stack's `Unsupported datatype for callbacks` path, and the generic escape hatch
was test-tool-only. A conformant B-LD was therefore not implementable.

That PR adds typed `Lighting_Command` adapters — the application supplies the six
fields as primitives and the stack assembles, encodes, and decodes the SEQUENCE.
This example is the first consumer.

The submodule is pinned to `56866997` on `feat/constructed-property-adapters-6x`.
**Re-pin to the merge commit on `6.x` once that PR lands.**

## Before you ship

This example is a tutorial, and it identifies itself as one. Everything in this
table is read by clients and shown to the operator in **every discovery tool on
the network**. Left as-is, your product appears on a real site announcing itself
as a Chipkin demo. None of it is cosmetic.

| Constant (`main.cpp`) | Ships as | Change it to |
|---|---|---|
| `VENDOR_IDENTIFIER` | `389` (Chipkin) | **Your** company's vendor ID. Assigned by ASHRAE, free: <https://bacnet.org/assigned-vendor-ids/> |
| `VENDOR_NAME` | `Chipkin Automation Systems` | Your company name - must match the vendor ID above. |
| `DEVICE_NAME` | `"Rainbow"` | Your luminaire's `Object_Name`. **Must be unique across the BACnet internetwork** - see the note below. |
| `MODEL_NAME` | `CAS BACnet Stack Example - B-LD` | Your model designation - what a building operator reads to identify your luminaire. |
| `DEVICE_DESCRIPTION` | a description of *this example* | What your luminaire actually is. |
| `FIRMWARE_REVISION` / `APPLICATION_SOFTWARE_VERSION` | `1.0.0` | Your real versions - wire them to your build. |
| `DCC_PASSWORD` | `""` (no password) | Set your device's secret, or leave empty to accept any DeviceCommunicationControl. It crosses the wire in **plaintext** - a guard against accidents, not a security boundary. |
| Device instance | `389016` (`--deviceID` overrides) | Must be unique on the internetwork. BACnet requires this to be configurable; keep it so. |

> **`Object_Name` uniqueness is the one that will bite you.** The device instance
> is runtime-configurable via `--deviceID`, but `DEVICE_NAME` is a compile-time
> constant. Ship two units and configure their instances correctly, and **both
> still announce `Object_Name "Rainbow"`** - a spec violation. In a real product,
> `Object_Name` must be per-unit configurable too (serial number, DIP switches,
> a config file, or a `--deviceName` argument).

`main.cpp` marks this block with a `CHANGE ALL OF THIS BEFORE YOU SHIP` banner.

## Build

```bash
git clone --recursive https://github.com/chipkin/BACnetProfileExample-B-LD-CPP.git
cd BACnetProfileExample-B-LD-CPP
cmake -B build -S .
cmake --build build --config Release
```

If you cloned without `--recursive`, run `git submodule update --init --recursive`
first. The first build compiles the whole CAS BACnet Stack (~600 source files) and
takes a few minutes; later incremental builds are fast.

## Run

```bash
./build/BACnetExampleBLD                       # Linux/macOS
.\build\Release\BACnetExampleBLD.exe           # Windows
```

Options: `--help`, `--version`, `--deviceID <n>` (default 389016), `--port <n>`
(default 47808). Interactive keys: `h` help, `q` quit, up/down nudge Analog
Input 1. The light is commanded over BACnet, not from the keyboard.

## Try it

With a BACnet client (e.g. the
[CAS BACnet Explorer](https://store.chipkin.com/products/tools/cas-bacnet-explorer)):

1. **Who-Is** → an I-Am from device **389016**, vendor **389**.
2. **ReadProperty** `Lighting Output 1` `Present_Value` → `0.0` (nothing has
   commanded it, so it rests at `Relinquish_Default` — the light is off).
3. **WriteProperty** `Lighting_Command` = `{operation: fadeTo, target-level: 75.0,
   fade-time: 3000}` → the console logs the fade and `Present_Value` reads `75.0`.
4. **ReadProperty** `Lighting_Command` → the command you just sent, read back.
5. **WriteProperty** `Lighting_Command` = `{operation: fadeTo, target-level: 50.0}`
   — **no fade-time**. The console shows it fading over **3000 ms**
   (`Default_Fade_Time`), not 0. That is the `use*` flag doing its job.
6. **WriteProperty** `Lighting_Command` = `{operation: stepUp}` → the light rises
   by `Default_Step_Increment` (5 %).
7. **WriteProperty** `Lighting_Command` with `target-level` = `150.0` → rejected
   with `value-out-of-range`.
8. **WriteProperty** `Present_Value` = `20.0` at priority 8 → the light goes to
   20 % directly, no fade. Both paths drive the same `Priority_Array`.
9. **TimeSynchronization** → the console logs the time the device would set.

## Versions

| | |
|---|---|
| Example version | 1.0.0 |
| `common/` helper | 1.3.0 |
| CAS BACnet Stack | 6.0.0.0 — pinned at `56866997` (needs [PR #240](https://github.com/chipkin/cas-bacnet-stack/pull/240)) |
| Protocol_Revision | 24 (the stack default — the highest it supports) |
| Verified on | Windows (MSVC 2022, C++17) |

## License

The example source code is dedicated to the public domain under
[CC0-1.0](LICENSE) — copy it into your project freely. The **CAS BACnet Stack is
a separate, commercially licensed product** and is not covered by that
dedication; contact [Chipkin](https://store.chipkin.com/) for licensing.
