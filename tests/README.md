# B-LD Wire Tests

Tests that drive the running lighting device over BACnet/IP from outside it and
fail when its Profile Function is removed. The Profile Function, from ANSI/ASHRAE
135-2024 Annex L.11.2: "A B-LD is any device that implements Binary Lighting
Output and/or Lighting Output objects" - so the tests prove the Lighting Output
behaves as cl. 12.54 says one does: fades and ramps take their time, stops hold,
priorities arbitrate, warns wait out the egress time, and bad commands and a
failed lamp are reported.

The tests are written against the series' shared harness in
[`../wiretest/`](../wiretest/README.md) (vendored, like `common/`); everything
specific to this example is here. Python 3 standard library only - nothing to
`pip install`.

## Running

Build the example (README "Build"), then from the repository root:

```bash
python3 tests/run_wire_tests.py --exe build/BACnetExampleBLD
```

On Windows, `--exe build\Release\BACnetExampleBLD.exe`. It ends with
`ALL WIRE TESTS PASSED` (exit 0) or the scripts that failed, after about a
minute. `--port` (default 48020) is the UDP port the test starts the example on.
CI (`.github/workflows/release.yml`) runs it on Linux after the smoke test. Each
script also runs on its own with the same arguments.

A `[RETRY]` line means a request went unanswered for 1 s and was sent again (the
Peer retries twice, as a BACnet client does). On Windows the example's UDP
receive (`common/` SimpleUDP) occasionally drops a datagram when the machine is
busy; the retry absorbs it, and the line keeps it visible.

## The setup

```
test client (127.0.0.1, ephemeral UDP port)  - the Peer
    |  BACnet/IP, unicast
BACnetExampleBLD  UDP --port                 - Device 389016, Lighting Output 1 "Jade"
```

The Peer is a Python BACnet client (`wiretest.Client`), never another example's
binary. It plays whatever commands the light on a real site: a lighting
supervisor, a Schedule, an operator workstation. It writes `Lighting_Command` (a
`BACnetLightingCommand`, `wiretest.services.lighting_command()`) and
`Present_Value`, and reads the light back. Fades are 1-2.5 s and egress times 5 s so a
run stays short; the checks sample `Tracking_Value` and `In_Progress` every
0.1 s.

`ld_setup.py` holds what the scripts share about this light (`Light`,
`sample_light()`, `reset()`). The generic helpers it once held are in `wiretest/`
0.7.0: `wiretest.services.lighting_command()` / `decode_lighting_command()`,
`wiretest.context_real()`, `wiretest.sample()`, `wiretest.sleep_until()`,
`wiretest.monotonic()`, and the short timeout with visible retries is
`wiretest.Client(retries=2, timeout=1.0)`.

## `discovery_test.py` - every listed property reads as a value

1. **Who-Is** (for 389016, unicast) -> the device's I-Am.
2. **Device `Object_List`** names exactly the Device, Lighting Output 1 and
   Network Port 1 - the profile's set. This is also the control: a walk over
   nothing would pass.
3. For each object, **`Property_List`** reads, and a ReadProperty of every
   property it lists - plus `Object_Identifier`, `Object_Name`, `Object_Type`
   and `Property_List`, which cl. 12.1.1.4.1 leaves out of the list - returns a
   ComplexACK. An Error, Reject, Abort or no answer prints an `[UNREADABLE]` line
   and fails the check.
4. Network Port 1's `IP_DNS_Server`, `FD_BBMD_Address` and
   `FD_Subscription_Lifetime` are listed and read (B-SS-CPP #20, #21, #22).

## `fade_test.py` - fadeTo takes its fade time (Table 12-67, cl. 12.54.4, 12.54.5)

Fades 0 -> 80 over 2.0 s, 80 -> 20 over 1.5 s, and 20 -> 60 with **no**
fade-time after writing `Default_Fade_Time` = 1500 ms. For each: `Present_Value`
and `Priority_Array[16]` are the target at once; `Tracking_Value` moves
monotonically, passes through intermediate levels, and stays within 8 points of
`start + (target - start) * t / fade-time`; `In_Progress` is `fadeActive` whenever
the level is part-way; after the fade time it has arrived, `In_Progress` is `idle`
and `Tracking_Value` equals `Present_Value`. Controls: the light starts off and
idle, and `Lighting_Command` reads `none` before anything is written; afterwards
it reads back the last command, fields as written.

## `ramp_step_test.py` - rampTo keeps its rate; the steps step (Table 12-67)

Ramps 0 -> 60 at 30 %/s and 60 -> 10 with no ramp-rate after writing
`Default_Ramp_Rate` = 40 %/s: monotonic, the rate measured from the samples within
15 %, `In_Progress` `rampActive` while part-way, arrival on time. Then
`stepUp` (default and given increment, clamped at 100 %), `stepDown` clamped at
1.0 %, `stepOff` from 1.0 % to 0, `stepUp` / `stepDown` ignored while off,
`stepOn` from off to 1.0 % and from 1.0 % up.

## `stop_priority_test.py` - stop holds; priorities arbitrate (Table 12-67, cl. 12.54.6.1)

- `stop` at another priority is ignored; `stop` at the fade's priority halts it
  part-way, writes `Tracking_Value` to the slot, `In_Progress` `idle`, and the
  level is still held after the fade would have ended.
- `Present_Value` written at priority 8 mid-fade (fade at 16) halts the fade: the
  light goes to the written level at once, `Priority_Array[16]` keeps the halted
  fade's target, and relinquishing 8 puts the light at that target at once (no
  `Transition`, cl. 12.54.19).
- `Present_Value` written at the **same** priority mid-fade halts it too ("implicitly
  halted"), and the old fade never takes the light to its target afterwards.
- A lower-priority write is stored but the fade keeps running and arrives.
- A fadeTo at a priority that is not in control is written to its slot but not
  executed.

## `warn_test.py` - blink-warn and egress time (Table 12-67, Table 12-65, cl. 12.54.15)

With `Egress_Time` = 5 s and the light at 100 % @ 9 (cl. 12.54's office example):
`warnRelinquish` sets `Egress_Active`, holds 100 % part-way through, then
relinquishes priority 9; `warnOff` writes 0.0 % at 9 instead; `stop` cancels the
egress timer and the light stays on; with priority 12 holding 40 %,
`warnRelinquish` @ 9 relinquishes at once (condition (c)); `Present_Value` -2.0
acts as `warnRelinquish` without being written to the array. Then
`Last_On_Value`, `restoreOn`, `toggleRestore` both ways, `defaultOn`, and `warn`
(level unchanged, no egress).

## `failure_test.py` - the Failure Modes (cl. 12.54.4, 12.54.6, 12.54.9, 12.54.11, 12.54.12, 12.54.16-18)

1. **A bad command is refused and changes nothing**: fade-time 50 ms,
   target-level 150 %, ramp-rate 0.05 %/s, step-increment 0, operation `none`,
   fadeTo without target-level, `Present_Value` 120 and -8.0 - each Error
   PROPERTY / VALUE_OUT_OF_RANGE, with the light, `Priority_Array[16]` and
   `Lighting_Command` unchanged; `Default_Fade_Time` 50, `Default_Ramp_Rate` 0 and
   `Default_Step_Increment` 101 refused the same way, old value kept. A valid
   fadeTo still works afterwards.
2. **Out_Of_Service decouples Reliability**: in service a `Reliability` write gets
   WRITE_ACCESS_DENIED; with `Out_Of_Service` TRUE (`Status_Flags`
   OUT_OF_SERVICE set) `Reliability` = `lampFailure` is accepted and sets FAULT,
   `Lighting_Command` still drives the light, and back in service `Reliability`
   follows the healthy lamp again.
3. **A burnt-out lamp** (a second example, started with the test-only
   `BLD_TEST_LAMP_BURNS_OUT=1`): `Reliability` `noFaultDetected` while off; switched
   on, the lamp burns out - `Reliability` `lampFailure`, `Status_Flags` FAULT - and
   the Lighting Output still carries out the command. Control: without the hook
   the lamp survives 100 %.

The stack range-checks the `Lighting_Command` fields an operation uses before the
example's callback sees them (out-of-range fade-time, ramp-rate, step-increment,
target-level); operation `none`, a missing target-level, the `Present_Value`
range and the `Default_*` ranges are checked by `main.cpp`. The mutation evidence
below covers the example's own checks.

## Results

Run 2026-10-16, stack `6.x` @ `64b2cfac5` (6.0.23), example v1.2.0 - see the
`profile-functional` commit message for the full record, including the mutation
results (each behaviour removed from `main.cpp` in turn, the named script failing,
then restored).
