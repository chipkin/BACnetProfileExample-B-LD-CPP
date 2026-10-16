# Tutorial - extending and reviewing the B-LD example

[README.md](README.md) says what this example *is*. This document is the *how*:
how to extend it into your own luminaire, who serves which property, how to
review the result for conformance, and what goes wrong when you get it subtly
right.

Read this once before you start changing `main.cpp`. The most expensive mistake
in this example is silent, and the section it lives in is
[Add a second Lighting Output](#add-a-second-lighting-output).

- [Extending the example](#extending-the-example)
- [The lighting engine and the lamp Simulation](#the-lighting-engine-and-the-lamp-simulation)
- [Serving a constructed (composite) property](#serving-a-constructed-composite-property)
- [What each object type needs you to serve](#what-each-object-type-needs-you-to-serve)
- [A Lighting Output's required properties](#a-lighting-outputs-required-properties)
- [Who serves what: the application or the stack?](#who-serves-what-the-application-or-the-stack)
- [Reviewing your device](#reviewing-your-device)
- [Troubleshooting](#troubleshooting)

## Extending the example

The example is intentionally small so it's easy to change.

**Change an object's value or name** - edit the constants / callbacks in
`main.cpp` (e.g. `g_defaultFadeTime`, or the `"Jade"` string in
`GetPropertyCharString`).

**Change the device identity before you ship** - vendor ID, vendor name, model
name, description, firmware revision, device name and the DeviceCommunicationControl
password are all in the `CHANGE ALL OF THIS BEFORE YOU SHIP` block at the top of
`main.cpp`, with a per-field note on each saying what to change it to. That block
is the authoritative checklist; it is in the source rather than here so it cannot
be skipped by someone who only reads the code.

### Add a second Lighting Output

Read this whole recipe before starting - the last step is the one that is easy
to miss and the one BTL will fail you for.

> **Why skipping a step is SILENT.** The `GetProperty*` callbacks match on
> **both** object type *and* instance (`objectInstance ==
> LIGHTING_OUTPUT_INSTANCE`, or `GetCommandable()`), so a new instance falls
> through every one of them.
>
> Here is the part that matters, and it is the opposite of what most people
> assume: falling through a callback does **not** reliably produce an
> error. The stack errors only for the few properties it refuses to invent -
> `Present_Value`, `Number_Of_States`, `Relinquish_Default`, `Local_Date`,
> `Local_Time`, and a Network Port's `APDU_Length`. For everything else it **silently substitutes a default**:
>
> | Property | If you forget to serve it | Loud? |
> |---|---|:--:|
> | `Present_Value` | Error (`read-access-denied`) | yes |
> | `Object_Name` | reads back as the string **`"undefined"`** | **no** |
> | `Tracking_Value`, `Last_On_Value`, `Default_On_Value` | read back as **`0.0`** | **no** |
> | `Default_Fade_Time` | reads back as **`0`** - an impossible fade time | **no** |
>
> **Doesn't the `errorCode` out-parameter fix this?** Only if you use it, and
> only where it is right to. Each `GetProperty*` callback ends with a
> `uint32_t* errorCode` that the stack presets to `success` and reads only when
> you return `false`, so you *can* turn any decline into a chosen BACnet error.
> But ending every callback with `*errorCode = unknown-property` breaks the
> device: the stack's decline-and-fabricate path is what answers required
> properties an application is not expected to serve. Set `errorCode` only where
> *this device* knows the request is wrong - the `SetProperty*` callbacks and
> `SetPropertyLightingCommand` do it for out-of-range writes, and
> `DeviceCommunicationControl` does it for a bad password.
>
> It is worse than "wrong value": the object's `Property_List` **still advertises**
> the property. So the object actively claims to have it, and then answers with a
> default. Nothing on the wire says you forgot anything. (Up to v1.1.3 this
> example did exactly that with `Last_On_Value` and `Default_On_Value`: listed,
> read as `0.0`, never served.)
>
> So a half-added object does not look broken; it looks **healthy**. Add two of
> them and both report `Object_Name "undefined"` - duplicate object names inside
> one device, which is a spec violation and a hard BTL failure that every scan
> tool will render as a perfectly good object. **"It scanned OK" is exactly the
> failure mode, not evidence against it.**

The engine in section 1b holds **one** light: `g_lightingOutput` (its
Priority_Array), `g_engine` (its fade/ramp/egress state and Tracking_Value),
`g_lightingCommand` (the last command) and the writable defaults. A second light
needs its own copy of each:

```cpp
// 1) Group one light's state into a struct, and keep one per instance.
//    Naming: a second object of a type is "<Colour> 2" - so Lighting Output 2 is
//    "Jade 2", NOT a new colour. Each object TYPE owns one colour series-wide.
struct Light {
    uint32_t instance;
    Commandable priorityArray;          // was g_lightingOutput
    LightingEngine engine;              // was g_engine
    LightingCommandState lastCommand;   // was g_lightingCommand
    uint32_t defaultFadeTime; float defaultRampRate; float defaultStepIncrement; uint32_t egressTime;
};
static Light g_lights[2] = { /* instance 1 "Jade", instance 2 "Jade 2" */ };

// 2) Make the engine functions take a Light* instead of using the globals, and
//    call LightingTick() for every light in the main loop.

// 3) Route EVERY callback by instance: GetCommandable(), every Lighting Output arm
//    of GetPropertyReal / Enumerated / UnsignedInteger / Bool / CharString, every
//    SetProperty* callback, and both Lighting_Command callbacks.

// 4) In main(): AddObject, SetPropertyEnabled(Reliability), the commandable and
//    writable calls - once per instance. Check every return.
```

Then run [`tests/discovery_test.py`](tests/README.md) (add the new object to its
`EXPECTED_OBJECTS`): it reads every property every object lists and fails on an
error. It cannot see a silently substituted `0.0`, so also read every property of
Lighting Output 2 and **diff it against Lighting Output 1**. Any property that comes
back `"undefined"` or `0` where object 1 returns something real is a step you
missed. Because the failure is silent (see the table above), this diff is the
only thing that catches it.

## The lighting engine and the lamp Simulation

`main.cpp` keeps them apart on purpose:

- **Section 1b, the engine, is real BACnet behaviour** and is what you keep. It
  turns a `Lighting_Command` into what cl. 12.54 requires over time:
  `Present_Value` is the target at once, `Tracking_Value` moves to it
  (proportionally over the fade time, or at the ramp rate), `In_Progress` is
  `fadeActive` / `rampActive` meanwhile, a warn holds the level for `Egress_Time`
  with `Egress_Active` TRUE. `ExecuteLightingOperation()` is Table 12-67 row by
  row, each row quoted; `HaltCommandInProgress()` and `HaltIfWriteOverrides()`
  are cl. 12.54.6.1. Every write path that touches the Priority_Array goes
  through `HaltIfWriteOverrides()` first - a new one must too, or a fade keeps
  running after a higher priority took the light.
- **Section 1c, the Simulation, is what you replace.** Drive your dimming driver
  from `g_engine.trackingValue` in `SimulationLampTick()`'s place, do the blink
  your fixture can do in `SimulationBlinkWarn()`, and set `g_lampFailed` from
  your driver's open-lamp detection. The test-only `BLD_TEST_LAMP_BURNS_OUT`
  hook goes with it.

`LightingTick()` runs on every pass of the main loop (about every millisecond
here). On hardware, call it at least as often as your dimmer can change level;
a slower tick only makes the steps coarser - the timing comes from a monotonic
clock, not from counting ticks.

**Why the example runs the engine itself:** the CAS BACnet Stack's customer
interface hands a `Lighting_Command` to the application as plain numbers
(`RegisterCallbackSetPropertyLightingCommand`) and stops there. The stack has a
Lighting Output engine of its own, but it is part of the test-tool interface,
which a product does not ship.

## Serving a constructed (composite) property

`Lighting_Command` is a **constructed** BACnet datatype - a SEQUENCE of an
operation plus several optional fields - not a primitive like REAL or
Enumerated. A plain typed callback (`GetPropertyReal`, `GetPropertyEnumerated`,
...) cannot serve it; the stack would answer *unsupported-datatype*. Instead you
register a **dedicated adapter callback** for that property type:

```cpp
// Register the Lighting_Command adapter callbacks (not the generic typed ones):
BACnetStack_RegisterCallbackGetPropertyLightingCommand(GetPropertyLightingCommand);
BACnetStack_RegisterCallbackSetPropertyLightingCommand(SetPropertyLightingCommand);
```

Your callback then works in the stack's **decoded field struct**, not raw bytes -
`GetPropertyLightingCommand` fills an operation + `use*` flags + values, and the
stack encodes the SEQUENCE on the wire. There is no BACnet byte-twiddling anywhere
in `main.cpp`.

**The `use*` flags are load-bearing, not decoration.** On the **get** side,
`false` omits the field from the SEQUENCE. On the **set** side, `false` means
**the writer omitted it** - and the accompanying value is meaningless. That
distinction is the whole reason the flags exist. Per cl. 12.54.6 Table 12-66, a `fadeTo` with
**no** `fade-time` means *"fade over `Default_Fade_Time`"* - **not** *"fade in
0 ms"*, which is what you would get if you naively trusted the value.
`SetPropertyLightingCommand` resolves each omitted optional to the light's own
default for exactly that reason - never trust `fadeTime`/`rampRate`/
`stepIncrement`/`priority` without first checking its `use*` flag.

This is the pattern for **any** constructed property (`BACnetDateTime`,
`BACnetLightingCommand`, ...): a typed adapter that speaks the decoded struct,
never the wire bytes.

## What each object type needs you to serve

The application must serve every REQUIRED property the stack does not generate.
It differs per type - this is the checklist, so you do not have to infer it:

| Object type | You must serve | Plus |
|---|---|---|
| Device | `Object_Name`, `Vendor_Name`, `Vendor_Identifier`, `Model_Name`, `Firmware_Revision`, `Application_Software_Version` | `Description` (optional, enabled) |
| Lighting Output | `Object_Name`, `Tracking_Value`, `Lighting_Command`, `In_Progress`, `Out_Of_Service`, `Blink_Warn_Enable`, `Egress_Time`, `Egress_Active`, `Default_Fade_Time`, `Default_Ramp_Rate`, `Default_Step_Increment`, `Relinquish_Default`, `Lighting_Command_Default_Priority`, `Last_On_Value`, `Default_On_Value` | `Present_Value` served via `Priority_Array` slots; `Reliability` (optional, enabled); no `Units` (see below) |
| Network Port | `Object_Name`, `Out_Of_Service`, the BACnet/IP addressing (`IP_Address`, `IP_Subnet_Mask`, `BACnet_IP_UDP_Port`, ...) | see [docs/PICS.md](docs/PICS.md) |

## A Lighting Output's required properties

Several exist on no other object in this series. Watch the units - they are not
consistent, and that is per spec:

| Property | Value here | Notes |
|---|---|---|
| `Tracking_Value` | the engine's level | What the light **is being driven at**, vs `Present_Value` = the **target**. Equal whenever `In_Progress` is `idle`; mid-fade it is "the current calculated value of the ramp or fade algorithm" (cl. 12.54.5) |
| `In_Progress` | `idle` / `fadeActive` / `rampActive` | What is running right now (a warn's egress time is `idle`: the level is held) |
| `Blink_Warn_Enable` | `true` | The "lights are about to go out" flash |
| `Egress_Time` | 30, writable | **seconds** |
| `Egress_Active` | `true` during a warn's egress time | cl. 12.54.15 |
| `Default_Fade_Time` | 3000, writable | **milliseconds**, 100 to 86400000 |
| `Default_Ramp_Rate` | 10.0, writable | % per second, 0.1 to 100 |
| `Default_Step_Increment` | 5.0, writable | %, 0.1 to 100 |
| `Lighting_Command_Default_Priority` | 16 | Priority a `Lighting_Command` writes at when it names none |
| `Last_On_Value` | 100.0 until it has been on | The last `Present_Value` >= 1.0 % (cl. 12.54.44); what `restoreOn` writes |
| `Default_On_Value` | 100.0 | What `defaultOn` writes (cl. 12.54.45) |
| `Reliability` | `noFaultDetected` / `lampFailure` | Optional, enabled; drives the FAULT flag of `Status_Flags`; writable only while `Out_Of_Service` is TRUE |

Note there is **no `Units`** row: a Lighting Output has no Units property (its
level is a dimensionless percent), so serving one would be dead code the stack
never calls.

## Who serves what: the application or the stack?

The single most common question when reading this file is "who answers this
property?" For the Lighting Output "Jade":

| Property | Served by | How |
|---|---|---|
| `Object_Identifier`, `Object_Type`, `Object_List`, `Property_List`, `Status_Flags` | **stack** | generated from the object you added |
| `Current_Command_Priority` | **stack** | computed from the Priority_Array (required at Protocol_Revision 30) |
| `Event_State` | not present | optional on a Lighting Output (required only with intrinsic reporting), and this example does no intrinsic reporting, so the object does not have it |
| `Present_Value` | **you (write) / stack (read)** | `SetPropertyReal` accepts a direct write of the REAL level (0-100%); on read the **stack computes** `Present_Value` from the Priority_Array slots that `GetPropertyReal` serves (highest non-null slot, or `Relinquish_Default`) |
| `Object_Name` | **you** | `GetPropertyCharString` |
| `Tracking_Value`, `In_Progress`, `Egress_Active`, `Reliability`, `Default_Fade_Time`, ... | **you** | typed Get callbacks (REAL / Enumerated / Unsigned / Bool), from the engine in section 1b |
| **`Lighting_Command`** | **you, via a constructed-property adapter** | `GetPropertyLightingCommand` / `SetPropertyLightingCommand` - see [above](#serving-a-constructed-composite-property) |

Every object, not just this one, is in [docs/PICS.md](docs/PICS.md).

Going beyond this (ReadPropertyMultiple, COV, alarms, scheduling) means
implementing a richer profile - see the series table in [README.md](README.md).

## Reviewing your device

After you have changed anything, review it against the conformance statement
rather than against "it looked fine in the explorer":

1. Regenerate [docs/PICS.md](docs/PICS.md) after editing `docs/objects.json`
   (see [Keeping the PICS honest](#keeping-the-pics-honest) below). A ⚠ row is a
   required property nothing serves.
2. Read **every** property listed for **every** object with a BACnet client, and
   compare the value against the PICS. `"undefined"`, `no-units` and `0` are three
   of the shapes a missed callback takes.
3. Diff a new object of a type against the existing one of that type. Anything
   that differs and shouldn't is a callback that matched on instance.
4. Confirm the services you do **not** implement are still rejected - for B-LD,
   ReadPropertyMultiple, SubscribeCOV, and UTCTimeSynchronization (the profile
   allows DM-TS-B *or* DM-UTC-B; this example does only DM-TS-B, and the stack
   itself rejects a UTCTimeSynchronization request before this example's
   callback is ever reached).
5. Write a `Lighting_Command` with an operation that requires `target-level`
   (`fadeTo`/`rampTo`) but omit it, and confirm the write is rejected rather
   than silently accepted with no effect.
6. Run the Wire Tests ([tests/README.md](tests/README.md)). They fail if the
   light snaps instead of fading, ignores a stop, lets a lower priority override
   a fade, or skips an egress time.

### Known limitation: Local_Date / Local_Time are dead code

`main.cpp` implements `GetPropertyDate` and `GetPropertyTime`, backed by
`g_syncedDateTime`, and `SetSystemTime` (the `TimeSynchronization` handler)
keeps that struct up to date - `CHANGELOG.md` describes this as fixed and
wire-tested. **But `Local_Date` and `Local_Time` are OPTIONAL Device
properties**, and nothing in `main.cpp` calls
`BACnetStack_SetPropertyEnabled(g_deviceInstance, OBJECT_TYPE_DEVICE,
g_deviceInstance, PROPERTY_IDENTIFIER_LOCAL_DATE / LOCAL_TIME, true)` for
either one - the same enable this file's own comment above the `SetPropertyEnabled`
calls warns about for `Description` ("a Description branch in the callback
without this enable is DEAD CODE"). The stack's `IsPropertyEnabled` check
(`BACnetDBObject::IsPropertyEnabled`) only returns true for a property present
in the object's enabled-property list; an optional property that was never
explicitly enabled is not in that list. So as shipped, a `ReadProperty` of
`Local_Date` or `Local_Time` never reaches `GetPropertyDate`/`GetPropertyTime`
at all - the stack answers `unknown-property` first. `docs/objects.json` and
`docs/PICS.md` record this precisely rather than listing the two properties as
served: see the Device object's note in [docs/PICS.md](docs/PICS.md#11-objects-and-properties).
If you need `Local_Date`/`Local_Time` to actually answer, add the two
`SetPropertyEnabled` calls next to the `Description` one in `main()`.

### Keeping the PICS honest

`docs/PICS.md` is partly generated. `docs/objects.json` describes each object and
who serves which property; the series tool regenerates the object tables from it
plus the stack's own `docs/property-profile-reference.md` at the pinned commit:

```bash
python tools/gen-objects-properties.py BACnetProfileExample-B-LD-CPP            # rewrite
python tools/gen-objects-properties.py BACnetProfileExample-B-LD-CPP --check    # fail if stale
```

(That tool lives in the example-series repository, not in this one. If you only
have this repository, edit the generated block by hand and keep it matching the
callbacks in `main.cpp`.)

When you add an object or a property to `main.cpp`, update `docs/objects.json`
in the same change and regenerate. The `app` list is what the callbacks serve;
`accepted` is for a required property you deliberately leave to the stack's
default, and each one needs a justification. Anything required, not in `app` and
not in `accepted`, comes out as a ⚠ row - that is a defect, not a feature. (An
*optional* property that is served but never enabled, like `Local_Date` /
`Local_Time` above, does not trigger a ⚠ - the generator only checks required
properties - so it is called out here in prose instead.)

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| On start-up the app prints a wall of red `Error:` lines but the device works | **Expected - this is not your bug.** Two benign sources, both from the stack's own debug logging: (1) the device receives its **own** broadcast I-Am and logs a decode cascade (*"Services is not supported service=[0]"* ... *"Failed to process the incoming NPDU"*) - any BACnet/IP device that listens for broadcasts hears itself; (2) a one-time *"UUID has not been set. A UUID must be set for the BACnetSC device to start."* - the stack starts a BACnet/SC datalink these IP-only examples never configure. It appears once and does not spam. On a healthy start-up roughly half the output is these lines. |
| CMake error: *"CAS BACnet Stack adapter not found under: ..."* | Submodules not initialized. Run `git submodule update --init --recursive` (or pass `-D CAS_STACK_DIR=...`). |
| `CASBACnetStackDLL.h: No such file or directory` | Same - submodules not checked out. |
| Windows: *"No CMAKE_CXX_COMPILER could be found"* | Install Visual Studio with the "Desktop development with C++" workload, then re-run from a fresh terminal. |
| First build seems stuck for minutes | Normal - it's compiling ~600 stack files. Only the first build is slow. |
| App prints *"Failed to bind UDP port 47808"* | Another BACnet program is already using 47808. Stop it, or run with `--port <n>`. |
| Client sends Who-Is but sees no I-Am | Firewall is blocking UDP 47808, or the client and device are on different subnets (Who-Is is a broadcast). Allow the port; test on the same subnet first. |
| Replies show an unexpected device instance or vendor | Another BACnet device is already answering on this host/port. On Linux/macOS two processes can share the port and both reply; on Windows the example asks for `SO_EXCLUSIVEADDRUSE` (`common/SimpleUDP.cpp`) so this shows up as a bind failure instead. Stop the other device, or use `--port`. |
| `WriteProperty Lighting_Command` accepted but the light never reaches the target level | Check the response: a `target-level` outside 0-100 %, or a `priority` outside 1-16, is rejected with `value-out-of-range`; a `fadeTo`/`rampTo` with no `target-level` is rejected the same way (Table 12-67 makes it a required field). If the write really was accepted, re-read `Present_Value` and `Current_Command_Priority` - a fadeTo written at a priority that is not in control is stored in its slot but not executed (Table 12-67). |
| `Tracking_Value` differs from `Present_Value` | Expected while `In_Progress` is `fadeActive` or `rampActive`: `Present_Value` is the target, `Tracking_Value` the level on its way there (cl. 12.54.4, 12.54.5). They are equal again when `In_Progress` reads `idle`. |
| `ReadProperty Local_Date` or `Local_Time` returns `unknown-property` even though `main.cpp` has `GetPropertyDate`/`GetPropertyTime` | This is the [known limitation](#known-limitation-local_date--local_time-are-dead-code) above, not a new bug - neither property is ever enabled with `SetPropertyEnabled`. |
| `UTCTimeSynchronization` is rejected | By design. This example enables only `SERVICE_TIME_SYNCHRONIZATION` (the profile allows DM-TS-B *or* DM-UTC-B, not both); the stack itself rejects the UTC variant with *"Services is not supported service=[9]"* before `main.cpp` is ever reached. |
