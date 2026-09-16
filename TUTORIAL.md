# Tutorial - extending and reviewing the B-LD example

[README.md](README.md) says what this example *is*. This document is the *how*:
how to extend it into your own luminaire, who serves which property, how to
review the result for conformance, and what goes wrong when you get it subtly
right.

Read this once before you start changing `main.cpp`. The most expensive mistake
in this example is silent, and the section it lives in is
[Add a second analog input](#add-a-second-analog-input).

- [Extending the example](#extending-the-example)
- [Serving a constructed (composite) property](#serving-a-constructed-composite-property)
- [What each object type needs you to serve](#what-each-object-type-needs-you-to-serve)
- [A Lighting Output's required properties](#a-lighting-outputs-required-properties)
- [Who serves what: the application or the stack?](#who-serves-what-the-application-or-the-stack)
- [Reviewing your device](#reviewing-your-device)
- [Troubleshooting](#troubleshooting)

## Extending the example

The example is intentionally small so it's easy to change.

**Change an object's value or name** - edit the constants / callbacks in
`main.cpp` (e.g. the initial value of `g_analogInput1Value`, or the `"Bronze"`
string in `GetPropertyCharString`).

**Change the device identity before you ship** - vendor ID, vendor name, model
name, description, firmware revision, device name and the DeviceCommunicationControl
password are all in the `CHANGE ALL OF THIS BEFORE YOU SHIP` block at the top of
`main.cpp`, with a per-field note on each saying what to change it to. That block
is the authoritative checklist; it is in the source rather than here so it cannot
be skipped by someone who only reads the code.

### Add a second analog input

Read this whole recipe before starting - the last step is the one that is easy
to miss and the one BTL will fail you for.

> **Why there are four edits, not three - and why skipping one is SILENT.**
> Most of the `GetProperty*` callbacks match on **both** object type *and*
> instance (`objectInstance == ANALOG_INPUT_INSTANCE`), so a new instance falls
> through every one of them. `GetPropertyBool` is the exception: it matches on
> type only, so `Out_Of_Service` works for a new instance for free.
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
> | `Units` | reads back as **`no-units` (95)** | **no** |
> | `Out_Of_Service` | served on type alone - works by accident | n/a |
>
> **Doesn't the `errorCode` out-parameter fix this?** Only if you use it, and
> only where it is right to. Each `GetProperty*` callback ends with a
> `uint32_t* errorCode` that the stack presets to `success` and reads only when
> you return `false`, so you *can* turn any decline into a chosen BACnet error.
> But ending every callback with `*errorCode = unknown-property` breaks the
> device: the stack's decline-and-fabricate path is what answers required
> properties an application is not expected to serve. Set `errorCode` only where
> *this device* knows the read is wrong - `SetPropertyLightingCommand` and
> `SetPropertyReal`/`SetPropertyEnumerated`/`SetPropertyUnsignedInteger` do it
> for out-of-range writes, and `DeviceCommunicationControl` does it for a bad
> password. The table above is still how the fall-through behaves on the Get
> side, and the diff below is still what catches a missed step.
>
> It is worse than "wrong value": the object's `Property_List` **still advertises
> `Units` (117)**. So the object actively claims to have the property, and then
> answers with a default. Nothing on the wire says you forgot anything.
>
> So a half-added object does not look broken; it looks **healthy**. Add two of
> them and both report `Object_Name "undefined"` - duplicate object names inside
> one device, which is a spec violation and a hard BTL failure that every scan
> tool will render as a perfectly good object. **"It scanned OK" is exactly the
> failure mode, not evidence against it.**

```cpp
// 1) a new instance number (in section 1).
//    Naming: a second object of a type is "<Colour> 2" - so Analog Input 2 is
//    "Bronze 2", NOT a new colour. Each object TYPE owns one colour series-wide.
static const uint32_t ANALOG_INPUT_2_INSTANCE = 2;   // "Bronze 2"
static float g_analogInput2Value = 23.1f;            // its live value

// 2) add the object (in main, next to the other BACnetStack_AddObject calls).
//    Check the return, like every other stack call in this file.
if (!BACnetStack_AddObject(g_deviceInstance, OBJECT_TYPE_ANALOG_INPUT, ANALOG_INPUT_2_INSTANCE)) {
    printf("Error: Failed to add Analog Input 2 (Bronze 2).\n");
    return 1;
}

// 3) serve its Present_Value + Object_Name:
//    GetPropertyReal:        AI/2 + Present_Value -> *value = g_analogInput2Value;
//    GetPropertyCharString:  AI/2 + Object_Name   -> "Bronze 2"

// 4) DO NOT SKIP: serve its Units, in GetPropertyEnumerated.
//    Units is a REQUIRED property of an Analog Input. The existing check reads
//    `objectInstance == ANALOG_INPUT_INSTANCE`, which is instance 1 - so without
//    this, reading Analog Input 2's Units returns an ERROR and the object is
//    NON-CONFORMANT. It will still appear in the Object_List and its
//    Present_Value will read back perfectly, so the device looks healthy right
//    up until BTL certification.
//    GetPropertyEnumerated:  AI/2 + Units -> *value = ENGINEERING_UNITS_DEGREES_CELSIUS;
```

Then re-run the README's Verify steps **against Analog Input 2**, not just Analog
Input 1 - read every required property and **diff it against Analog Input 1**.
Any property that comes back `"undefined"`, `no-units`, or `0` where object 1
returns something real is a step you missed. Because the failure is silent (see
the table above), this diff is the only thing that catches it.

The same rule applies to a second commandable output, or a second Lighting
Output: `GetCommandable()` (which every commandable REAL/enumerated/unsigned
callback and both `Lighting_Command` callbacks route through) matches on exact
`(objectType, objectInstance)`, so a new instance needs its own entry there too.

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
distinction is the whole reason the flags exist. Per cl. 12.54.9, a `fadeTo` with
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
| Analog Input | `Present_Value` (Real), `Object_Name`, `Units` | - |
| Binary Input | `Present_Value` (Enumerated), `Object_Name` | `Polarity` |
| Multi-State Input | `Present_Value` (Unsigned), `Object_Name` | `Number_Of_States` |
| Analog Output | `Object_Name`, `Units`, `Relinquish_Default` | `Present_Value` served via `Priority_Array` slots |
| Binary Output | `Object_Name`, `Polarity`, `Relinquish_Default` | `Present_Value` served via `Priority_Array` slots |
| Multi-State Output | `Object_Name`, `Number_Of_States`, `Relinquish_Default` | `Present_Value` served via `Priority_Array` slots |
| Lighting Output | `Object_Name`, `Tracking_Value`, `Lighting_Command`, `In_Progress`, `Blink_Warn_Enable`, `Egress_Time`, `Egress_Active`, `Default_Fade_Time`, `Default_Ramp_Rate`, `Default_Step_Increment`, `Relinquish_Default`, `Lighting_Command_Default_Priority` | `Present_Value` served via `Priority_Array` slots; no `Units` (see below) |

## A Lighting Output's required properties

Several exist on no other object in this series. Watch the units - they are not
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

Note there is **no `Units`** row: a Lighting Output has no Units property (its
level is a dimensionless percent), so serving one would be dead code the stack
never calls.

## Who serves what: the application or the stack?

The single most common question when reading this file is "who answers this
property?" For the Lighting Output "Jade":

| Property | Served by | How |
|---|---|---|
| `Object_Identifier`, `Object_Type`, `Object_List`, `Property_List`, `Status_Flags` | **stack** | generated from the object you added |
| `Current_Command_Priority` | **stack** | computed from the Priority_Array (required at Protocol_Revision 24) |
| `Event_State` | **stack**, sort of | no intrinsic alarming here, so nothing serves it - it reads `normal` only because `normal` is the enumeration's zero value and the stack substitutes a datatype default. Correct by coincidence, not design. |
| `Present_Value` | **you (write) / stack (read)** | `SetPropertyReal` accepts a direct write of the REAL level (0-100%); on read the **stack computes** `Present_Value` from the Priority_Array slots that `GetPropertyReal` serves (highest non-null slot, or `Relinquish_Default`) |
| `Object_Name` | **you** | `GetPropertyCharString` |
| `Tracking_Value`, `In_Progress`, `Egress_Time`, `Default_Fade_Time`, ... | **you** | typed Get callbacks (REAL / Enumerated / Unsigned / Bool) |
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
| `WriteProperty Lighting_Command` accepted but the light never reaches the target level | Check the response: a `target-level` outside 0-100 %, or a `priority` outside 1-16, is rejected with `value-out-of-range`; a `fadeTo`/`rampTo` with no `target-level` is rejected the same way (cl. 12.54.9 requires it). If the write really was accepted, re-read `Present_Value` - a lower-priority command can be masked by a still-active higher-priority one in the `Priority_Array`. |
| `ReadProperty Local_Date` or `Local_Time` returns `unknown-property` even though `main.cpp` has `GetPropertyDate`/`GetPropertyTime` | This is the [known limitation](#known-limitation-local_date--local_time-are-dead-code) above, not a new bug - neither property is ever enabled with `SetPropertyEnabled`. |
| `UTCTimeSynchronization` is rejected | By design. This example enables only `SERVICE_TIME_SYNCHRONIZATION` (the profile allows DM-TS-B *or* DM-UTC-B, not both); the stack itself rejects the UTC variant with *"Services is not supported service=[9]"* before `main.cpp` is ever reached. |
