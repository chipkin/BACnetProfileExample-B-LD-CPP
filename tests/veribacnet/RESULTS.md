# VeriBACnet results

The latest VeriBACnet run of this folder's project, summarised by hand from
that run's `report.json`. The run's own Results Folder (reports, packet
captures, wire logs) is not published: it holds the testing machine's network
addresses.

| | |
|---|---|
| Date | 2026-10-30 |
| Example | BACnet B-LD (Lighting Device) Example - C++ v1.3.0 (`common/` 3.5.0), CAS BACnet Stack `6.x` @ `69b6249f` |
| Profile | B-LD (BACnet Lighting Device) |
| Transport | BACnet/IP, UDP port 47830 |
| VeriBACnet | 0.20.0, a later build (its test device uses CAS BACnet Stack 6.0.23.0) |
| Test plan | 82 BTL tests (ANSI/ASHRAE 135.1-2023) selected for the B-LD profile and the options this example claims |
| Result | **52 PASS · 0 FAIL · 0 ERROR · 30 SKIP** |

**Judged BTL-clean on BACnet/IP**: no test failed or errored, and every skipped
test has a stated reason. See "What BTL-clean means" in [README.md](README.md).
This is not BTL certification.

**Measured coverage:** 52 of the 82 selected tests ran and all 52 passed. Of
the 30 skipped, 11 wait on a test-tool or test-script fix (tracked: the
tracking and blink-warn tests are still operator-guided placeholders), 4 need
an operator, and 15 do not apply to this device (it cannot create, delete or
rename objects over BACnet, has no writable fixed-size array,
optional-functionality property or non-commandable Present_Value, refuses the
deprecated DISABLE value as it should, initiates nothing that
disable-initiation stops, and the Relinquish Default test covers only Analog,
Binary and Multi-state objects).

**DeviceCommunicationControl's disable-initiation** (the device stops
initiating while disabled and resumes after) does not apply: the project
declares that this device initiates only I-Am in answer to Who-Is and I-Have in
answer to Who-Has, and BACnet lets both continue while initiation is disabled
(checked by hand: both are still answered). The four tests (9.24.1.6, .8,
.9, .10) therefore take the clause's own skip. The device also broadcasts one
I-Am when it starts, which is not an answer to a Who-Is; that start-up
announcement cannot be provoked while a test runs and is not declared. The test
that ran, 9.24.1.11 (the deprecated DISABLE is refused), passed.

**Measured in part:** the Lighting Output's Lighting_Command operations. The
NONE test and the fade, ramp and step tests (7.3.2.39.3 to 7.3.2.39.9) send
Lighting_Command and all seven pass. The two tracking tests and the nine
blink-warn tests (7.3.1.27.1 to 7.3.1.27.9) are still operator-guided
placeholders in the test tool (tracked). This example's own Wire Tests cover
those: fades, ramps, steps, stop, priority override, blink-warn with egress
time, and both failure modes.

This run replaces the 2026-10-26 run (82 tests, 50 PASS, 1 FAIL). What
changed: no example code changed. The Write Support test (7.2.2) now passes
(the test script no longer writes the Lighting Output's special value -1.0),
the Writing a Non-writable Property test (9.22.2.1) now finds the Lighting
Output's writable properties and passes, and the disable-initiation tests take
the clause's skip because the project declares the services the device
initiates.

## Tests that did not pass

| Test | Result | Why |
|---|---|---|
| 9.24.1.6, 9.24.1.8, 9.24.1.9, 9.24.1.10 DeviceCommunicationControl disable-initiation tests | SKIP | Not applicable: the project declares the device initiates only I-Am and I-Have (in answer to Who-Is and Who-Has), which disable-initiation does not stop (see above); the test tool takes the clause's own skip. |
| 7.3.1.27.1 to 7.3.1.27.9 Blink-Warn tests (WARN, WARN_OFF, WARN_RELINQUISH, STOP, failure and halted cases) | SKIP | The scripts are operator-guided placeholders, so they skipped in an unattended run (tracked). The device's own Wire Tests check every blink-warn command. |
| 7.3.2.39.1 Lighting Output Tracking Test | SKIP | Same: an operator-guided placeholder, tracked. |
| 7.3.2.39.2 Lighting Output Present_Value between 0.0 and 1.0 Test | SKIP | Same as 7.3.2.39.1. |
| 7.3.1.2 Relinquish Default Test | SKIP | The clause applies to Analog, Binary and Multi-state Output and Value objects; this device's commandable object is a Lighting Output. Does not apply. |
| 7.3.2.10.9 Ensure Device Object_Name is Configurable | SKIP | Needs an operator: the name is configured by restarting the device with `--deviceName`, which an unattended run cannot do. |
| 7.3.2.10.10 Ensure Device Object_Identifier is Configurable | SKIP | Same as 7.3.2.10.9, with `--deviceID`. |
| 9.32.1.12 Who-Has After Object_Name Changed | SKIP | Same as 7.3.2.10.9: only the Device's name can change, and only by a restart. |
| 9.32.1.13 Who-Has After Object_Identifier Changed | SKIP | Same as 7.3.2.10.10. |
| 7.3.2.10.3 Database_Revision after creating an object | SKIP | The device cannot create objects; the clause skips the test then. |
| 7.3.2.10.4 Database_Revision after deleting an object | SKIP | The device cannot delete objects; the clause skips the test then. |
| 7.3.2.10.5 Database_Revision after changing an Object_Name | SKIP | Only the Device's name can change, and only by a restart; the test does not apply. |
| 7.3.2.10.6 Database_Revision after changing an Object_Identifier | SKIP | No other object's identifier can change; the test does not apply. |
| 9.24.1.1, 9.24.1.3, 9.24.1.4 DeviceCommunicationControl DISABLE tests | SKIP | They use the deprecated DISABLE value, which a device at Protocol_Revision 20 or later must refuse (9.24.1.11, which passed, checks that it does). Not applicable. |
| 9.22.2.10 Resizing a writable fixed size array property | SKIP | Needs a writable fixed-size array; this device has none. |
| 9.22.2.11 Writing a Property Value Related to Non-supported Optional Functionality | SKIP | Needs a property tied to optional functionality the device does not support; this device has none. |
| 9.22.1.6 Writing NULL to Non-commandable Properties | SKIP | The device has no writable non-commandable Present_Value (the Lighting Output's is commandable), so the BTL Test Plan skips the test. |

The run used the example's shipped default, no DeviceCommunicationControl
password: the password is a constant in `main.cpp`, empty by default, not a
command-line option. Both TimeSynchronization tests (9.30.1.1 and 9.30.1.2)
passed.

No public issue has been opened for any of these.
