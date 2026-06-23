# Plan: B-LD (Lighting Device) — C++ example

**Profile:** B-LD · **Family:** Annex L.11 (Lighting Controller) · **Role:** B
(device/server) · **Archetype:** Specialized-object device · **Difficulty:** 3/5 ·
**Build wave:** 1 (per [master plan](../../bacnet-profile-examples-master-plan.md) §6)

A **B-LD** models a simple networked lighting device — a dimmer or a relay pack —
whose lighting channels are **commanded** by a controller and that keeps its clock
in step with the system. This example = the **B-SS baseline** + **commandable
lighting objects** (Lighting Output, Binary Lighting Output) + **DeviceComm­
unicationControl** + **time synchronization**. It is the canonical source for two
shared features (**F-LIGHT**, **F-TIMESYNC**) that later examples copy.

> Reference examples to copy from: [B-SA](../../BACnetProfileExample-B-SA-CPP)
> (commandable outputs), [B-ASC](../../BACnetProfileExample-B-ASC-CPP) (DCC).

---

## 1. What the profile requires

From `profiles.md` (L.11): `DS-RP-B, DS-WP-B, (DS-BLO-B or DS-LO-B); DM-DDB-B,
DM-DOB-B, DM-DCC-B, (DM-TS-B or DM-UTC-B)`. We implement **both** DS-LO-B and
DS-BLO-B (one Lighting Output + one Binary Lighting Output) so the example shows
both lighting object types; the profile only requires one.

| Required BIBB | Service to enable | Why |
|---|---|---|
| DS-RP-B | `SERVICE_READ_PROPERTY` (already on) | baseline — read any property |
| DS-WP-B | `SERVICE_WRITE_PROPERTY` (15) | command the lighting outputs (F-OUTPUTS) |
| DS-LO-B / DS-BLO-B | *(no service — object support)* | the Lighting Output / Binary Lighting Output objects must exist and be readable/writable |
| DM-DDB-B | *(Who-Is/I-Am — baseline)* | discovery |
| DM-DOB-B | *(Who-Has/I-Have — baseline)* | object discovery |
| DM-DCC-B | `SERVICE_DEVICE_COMMUNICATION_CONTROL` (17) | accept stop/resume comms (F-DCC) |
| DM-TS-B **or** DM-UTC-B | `SERVICE_TIME_SYNCHRONIZATION` (24) and/or `SERVICE_UTC_TIME_SYNCHRONIZATION` (25) | accept a clock set (F-TIMESYNC) |

**Deliberately omitted** (not required by B-LD): alarming/events (no AE-*),
scheduling (no SCHED-*), trending (no T-*), COV. The **Lighting_Command** fade/ramp
engine is *optional* per clause 12.54 and **not required by B-LD** — we omit it and
serve the lighting outputs as ordinary commandable points (see §6).

## 2. Objects this example exposes

```
Device 389010  "Rainbow"   (Vendor 389 - Chipkin Automation Systems)
    ├── Analog Input 1          "Bronze"     (baseline; REAL °C, read-only)
    ├── Binary Input 1          "Emerald"    (baseline; active/inactive, read-only)
    ├── Multi-State Input 1     "Hot Pink"   (baseline; state 1..3, read-only)
    ├── Lighting Output 1       "Amber"      (NEW; REAL 0..100 %, WRITABLE/commandable)
    ├── Binary Lighting Output 1 "Jade"      (NEW; on/off, WRITABLE/commandable)
    └── Network Port 1          "Vermilion"  (baseline)
```

Default device instance: **389010** (distinct from B-SS's 389001 so they coexist;
`--deviceID` overrides).

> **Colours (canonical):** **Amber** = Lighting Output, **Jade** = Binary Lighting
> Output — now in the runbook colour table, so B-LS reuses the same names. One
> canonical colour per object type across the series.

## 3. Shared features pulled in

| F-ID | Feature | Define / reuse | Copy from |
|---|---|---|---|
| F-OUTPUTS | Commandable outputs (Priority_Array + Relinquish_Default + Get/Set callbacks) | **reuse** | [B-SA](../../BACnetProfileExample-B-SA-CPP) `main.cpp` (the `Commandable` struct + Get/Set/Null callbacks) |
| F-DCC | DeviceCommunicationControl | **reuse** | [B-ASC](../../BACnetProfileExample-B-ASC-CPP) `main.cpp` |
| F-LIGHT | Lighting Output + Binary Lighting Output objects | **DEFINE** (canonical source) | new — per runbook + clause 12.54/12.55 |
| F-TIMESYNC | TimeSync / UTCTimeSync (DM-TS-B / DM-UTC-B) | **DEFINE** (canonical source) | new — per runbook |

Because B-LD **defines** F-LIGHT and F-TIMESYNC, write them carefully — **B-LS**,
**B-LSC**, **B-ALSC**, **B-ACC**, **B-AACC**, **B-EC**, **B-AEC**, and **B-BC**
copy them.

## 4. Required properties to serve

Baseline objects (AI/BI/MSI, Device, Network Port): identical to B-SS — no change.

**Lighting Output 1 (commandable, REAL):** the stack auto-generates the `S`
properties. The application supplies via callbacks:
- `Object_Name` (A) → "Amber" (GetPropertyCharString)
- `Out_Of_Service` (A) → false (GetPropertyBool)
- `Present_Value` — **do NOT serve** (commandable; stack derives it from the
  Priority_Array slots + Relinquish_Default — F-OUTPUTS; runbook gotcha 13)
- `Priority_Array` (1..16) + `Relinquish_Default` — serve via the F-OUTPUTS Real
  getter; accept writes via SetPropertyReal/SetPropertyNull
- **Confirm in `CASBACnetStackDLL.h`** which of Lighting Output's other required
  rev-24 properties (`Tracking_Value`, `In_Progress`, `Blink_Warn_Enable`,
  `Egress_Time`, `Egress_Active`, `Lighting_Command`, `Default_Fade_Time`,
  `Default_Ramp_Rate`, `Default_Step_Increment`) the stack auto-serves vs. need
  `SetPropertyEnabled` + a callback value (see §8 open question).

**Binary Lighting Output 1 (commandable, enumerated on/off):** like a Binary
Output (reuse the B-SA BO pattern) plus `Blink_Warn_Enable`, `Egress_Time`,
`Egress_Active`, `Feedback_Value`, `Polarity`. Serve Present_Value as commandable
(enumerated getter); confirm the rev-24 required set as above.

## 5. main.cpp section-by-section (delta from B-SA)

Start from a copy of **B-SA** (it already has the three inputs + commandable
outputs + the run loop), then:

- **§1 Constants:** rename app to `"BACnet B-LD (Lighting Device) Example - C++"`,
  device default `389010`, description names B-LD. Replace the AO/BO/MSO instance
  constants with `LIGHTING_OUTPUT_INSTANCE = 1` ("Amber") and
  `BINARY_LIGHTING_OUTPUT_INSTANCE = 1` ("Jade"). Keep one `Commandable` for each.
- **§2 Callbacks:**
  - Reuse the B-SA Real getter/setter for Lighting Output's Priority_Array /
    Relinquish_Default (REAL), and an enumerated getter/setter + Null setter for
    Binary Lighting Output (copy B-SA's BO handling).
  - Add the **F-DCC** callback (copy B-ASC verbatim).
  - Add the **F-TIMESYNC** handling: register
    **`BACnetStack_RegisterCallbackSetSystemTime`** (confirmed present in the pinned
    header). The stack receives a TimeSynchronization / UTCTimeSynchronization
    request and calls this callback with the new (y/m/d/h/m/s) value; the app sets
    its clock so the value `HelperGetSystemTime` returns reflects it. (The
    `BACnetStack_Send*TimeSynchronization` functions are the A-side *initiate*
    calls — not what a B-side device needs.)
- **§3 main():** `AddObject(OBJECT_TYPE_LIGHTING_OUTPUT, 1)` and
  `AddObject(OBJECT_TYPE_BINARY_LIGHTING_OUTPUT, 1)`; enable services 15, 17, 24/25;
  `SetPropertyWritable(Present_Value)` on both outputs (F-OUTPUTS); register the
  Get/Set/DCC/time-sync callbacks; `SendIAm`. Run loop unchanged.
- **Interactive keys:** keep h/q/up/down (up/down nudge the Lighting Output's
  relinquish-default or a manual slot for a visible demo — match B-SA's key
  semantics so the series stays uniform).

## 6. Stack gaps / TODO.md

**One optional-feature note, not a blocker.** The Lighting_Command fade/ramp
behaviour (smooth dim over a duration) is part of the Lighting Output object but is
**optional** and **not required by B-LD** (clause 12.54; profiles.md notes the
fade/ramp engine is 🟡 at the object-type level but "NOT required by the B-LD
profile"). We serve the lighting outputs as plain commandable points and write a
short `TODO.md §1` stating fade/ramp is intentionally omitted and what enabling it
would entail. Otherwise **no stack gaps — B-LD is fully implementable on the
standard DLL** (profiles.md: ✅ Sprint 61, DS-LO-B + DS-BLO-B verified end-to-end).

## 7. Verification

- [ ] Who-Is → I-Am from 389010, vendor 389; start-up I-Am broadcast
- [ ] Object_List lists all 6 objects; Protocol_Revision = 24
- [ ] every required property of Lighting Output 1 and Binary Lighting Output 1
      reads back (esp. Priority_Array all 16 slots + Relinquish_Default)
- [ ] WriteProperty Present_Value @priority 8 on Lighting Output → read-back shows
      the commanded value; WriteProperty NULL @8 relinquishes; effective
      Present_Value follows highest non-null slot (F-OUTPUTS behaviour)
- [ ] same for Binary Lighting Output (on/off)
- [ ] DeviceCommunicationControl disable-initiation accepted; device still answers
      reads (F-DCC; runbook DM-DCC-B reference)
- [ ] TimeSynchronization / UTCTimeSynchronization request updates the device clock
      (read Local_Date/Local_Time or observe time-stamped behaviour)
- [ ] WriteProperty to a read-only input (Bronze) is rejected
- [ ] builds clean Windows + Linux; `--port`/`--deviceID`/h/q/up/down work

## 8. Open questions

1. **Lighting Output rev-24 required-property set.** Confirm against
   `CASBACnetStackDLL.h` exactly which of `Tracking_Value`, `In_Progress`,
   `Blink_Warn_Enable`, `Egress_Time`, `Egress_Active`, `Lighting_Command`,
   `Default_Fade_Time`, `Default_Ramp_Rate`, `Default_Step_Increment` the stack
   auto-generates vs. which need `SetPropertyEnabled` + a served value. Same for
   Binary Lighting Output (`Feedback_Value`, `Polarity`, `Blink_Warn_Enable`,
   `Egress_*`). This determines the exact callback bodies — resolve empirically by
   reading every property back (runbook §5).
2. **Time-sync callback API — resolved.** Use
   `BACnetStack_RegisterCallbackSetSystemTime` (confirmed in the pinned header); the
   app stores the supplied time and returns it from `HelperGetSystemTime`. This is
   **F-TIMESYNC's canonical definition** — 8 later examples copy it, so verify the
   round-trip (send a TimeSync, read the device clock back) when you build it.
3. **Colours — resolved.** Amber (Lighting Output) + Jade (Binary Lighting Output)
   are in the runbook colour table; B-LS reuses them.
