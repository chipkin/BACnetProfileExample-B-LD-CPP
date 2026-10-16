#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
# Public-domain example code (CC0) - see ../LICENSE.
"""B-LD Wire Test: the Failure Modes cl. 12.54 defines (DS-LO-B).

    python3 tests/failure_test.py [--exe build/BACnetExampleBLD] [--port 48020]

1. A bad command is refused and changes nothing. ANSI/ASHRAE 135-2024 cl. 12.54.6:
   "Lighting commands written with a required or optional field, explicitly specified
   for this command, which are outside of the allowable range of values, shall cause a
   Result(-) to be returned with an 'Error Class' of PROPERTY and an 'Error Code' of
   VALUE_OUT_OF_RANGE." Table 12-67 NONE: "This operation shall not be written to the
   Lighting_Command property" (same error). Cl. 12.54.4: Present_Value outside 0.0% to
   100.0% (other than the special values) - same error. Cl. 12.54.16 / 12.54.17:
   Default_Fade_Time / Default_Ramp_Rate outside their ranges - same error.

2. A burnt-out lamp is reported. Cl. 12.54.11 Reliability "provides an indication of
   whether the Present_Value or the operation of the physical output in question is
   'reliable'"; cl. 12.54.9 Status_Flags FAULT is "Logical TRUE (1) if the Reliability
   property is present and does not have a value of NO_FAULT_DETECTED". The lamp is the
   example's Simulation; the test-only environment variable BLD_TEST_LAMP_BURNS_OUT=1
   makes it burn out the first time it is switched on. The light must keep obeying
   commands - BACnet still works, the lamp does not.

3. Out_Of_Service decouples Reliability for testing. Cl. 12.54.12: when Out_Of_Service
   is TRUE "(b) the Reliability property ... shall be decoupled from the physical
   output; (c) the Present_Value property and the Reliability property ... shall be
   writable to allow simulating specific conditions or for testing purposes". In
   service, the example refuses a Reliability write (WRITE_ACCESS_DENIED): it is the
   lamp's to say.
"""
import sys
import time

import ld_setup as setup
from ld_setup import (FADE_TO, IDLE, LAMP_FAILURE, NO_FAULT_DETECTED, NONE, RAMP_TO, SLACK, STATUS_FLAG_FAULT,
                      STATUS_FLAG_OUT_OF_SERVICE, STEP_UP, acked, application_boolean, application_enumerated,
                      application_real, application_unsigned, describe, value_out_of_range, wait_until)
import wiretest
from wiretest import record


def fault_flag(light):
    flags = light.value(setup.PROPERTY_STATUS_FLAGS)
    return flags[STATUS_FLAG_FAULT] if isinstance(flags, list) and len(flags) == 4 else f"read {flags}"


def refused_and_unchanged(light, label, write):
    """`write()` must be answered PROPERTY / VALUE_OUT_OF_RANGE and leave the light,
    Priority_Array[16] and Lighting_Command as they were."""
    before = (light.state(), light.value(setup.PROPERTY_PRIORITY_ARRAY, 16),
              light.read(setup.PROPERTY_LIGHTING_COMMAND).value_octets)
    answer = write()
    time.sleep(0.2)   # long enough for a wrongly-accepted fade to have moved the light
    after = (light.state(), light.value(setup.PROPERTY_PRIORITY_ARRAY, 16),
             light.read(setup.PROPERTY_LIGHTING_COMMAND).value_octets)
    record(f"{label}: Error PROPERTY / VALUE_OUT_OF_RANGE", value_out_of_range(answer), describe(answer))
    record(f"{label}: the light, Priority_Array[16] and Lighting_Command are unchanged", before == after,
           f"before {before[:2]}, after {after[:2]}")


def bad_commands(light):
    # A level to compare against: 50% @ 16, idle.
    light.write(setup.PROPERTY_PRESENT_VALUE, application_real(50.0), priority=16)
    record("Control: the light is at 50% @ 16 and idle", light.state() == (50.0, 50.0, IDLE),
           f"read {light.state()}")
    refused_and_unchanged(light, "fadeTo with fade-time 50 ms (range 100..86400000)",
                          lambda: light.command(FADE_TO, target_level=80.0, fade_time=50))
    refused_and_unchanged(light, "fadeTo target-level 150% (range 0..100)",
                          lambda: light.command(FADE_TO, target_level=150.0, fade_time=1000))
    refused_and_unchanged(light, "rampTo ramp-rate 0.05 %/s (range 0.1..100)",
                          lambda: light.command(RAMP_TO, target_level=80.0, ramp_rate=0.05))
    refused_and_unchanged(light, "stepUp step-increment 0 (range 0.1..100)",
                          lambda: light.command(STEP_UP, step_increment=0.0))
    refused_and_unchanged(light, "operation NONE",
                          lambda: light.command(NONE))
    refused_and_unchanged(light, "fadeTo with no target-level (a required field)",
                          lambda: light.command(FADE_TO, fade_time=1000))
    refused_and_unchanged(light, "Present_Value 120 @ 16",
                          lambda: light.write(setup.PROPERTY_PRESENT_VALUE, application_real(120.0), priority=16))
    refused_and_unchanged(light, "Present_Value -8.0 @ 16 (not a special value)",
                          lambda: light.write(setup.PROPERTY_PRESENT_VALUE, application_real(-8.0), priority=16))
    for property_identifier, name, octets, readback in (
            (setup.PROPERTY_DEFAULT_FADE_TIME, "Default_Fade_Time 50 ms", application_unsigned(50), 3000),
            (setup.PROPERTY_DEFAULT_RAMP_RATE, "Default_Ramp_Rate 0 %/s", application_real(0.0), 10.0),
            (setup.PROPERTY_DEFAULT_STEP_INCREMENT, "Default_Step_Increment 101 %", application_real(101.0), 5.0)):
        answer = light.write(property_identifier, octets)
        record(f"{name}: Error PROPERTY / VALUE_OUT_OF_RANGE and the old value kept",
               value_out_of_range(answer) and light.value(property_identifier) == readback,
               f"{describe(answer)}; reads {light.value(property_identifier)}")
    # The light still obeys a good command after all that.
    answer = light.command(FADE_TO, target_level=70.0, fade_time=300)
    time.sleep(0.3 + SLACK)
    record("after the refusals a valid fadeTo 70 still works", acked(answer) and light.state() == (70.0, 70.0, IDLE),
           f"read {light.state()}")


def out_of_service(light):
    record("Control: in service, Reliability NO_FAULT_DETECTED, FAULT flag clear",
           light.value(setup.PROPERTY_RELIABILITY) == NO_FAULT_DETECTED and fault_flag(light) is False)
    answer = light.write(setup.PROPERTY_RELIABILITY, application_enumerated(LAMP_FAILURE))
    record("in service, a Reliability write is refused with WRITE_ACCESS_DENIED - the lamp decides",
           answer.error == (setup.ERROR_CLASS_PROPERTY, setup.ERROR_CODE_WRITE_ACCESS_DENIED) and
           light.value(setup.PROPERTY_RELIABILITY) == NO_FAULT_DETECTED, describe(answer))
    answer = light.write(setup.PROPERTY_OUT_OF_SERVICE, application_boolean(True))
    flags = light.value(setup.PROPERTY_STATUS_FLAGS)
    record("Out_Of_Service TRUE is accepted and sets Status_Flags OUT_OF_SERVICE",
           acked(answer) and isinstance(flags, list) and flags[STATUS_FLAG_OUT_OF_SERVICE] is True,
           f"{describe(answer)}; Status_Flags {flags}")
    answer = light.write(setup.PROPERTY_RELIABILITY, application_enumerated(LAMP_FAILURE))
    record("out of service, Reliability LAMP_FAILURE can be written (cl. 12.54.12 (c)) and sets FAULT",
           acked(answer) and light.value(setup.PROPERTY_RELIABILITY) == LAMP_FAILURE and fault_flag(light) is True,
           f"{describe(answer)}; FAULT {fault_flag(light)}")
    answer = light.command(FADE_TO, target_level=20.0, fade_time=300)
    time.sleep(0.3 + SLACK)
    record("out of service, Lighting_Command still drives Present_Value (cl. 12.54.12 (e))",
           acked(answer) and light.state() == (20.0, 20.0, IDLE), f"read {light.state()}")
    answer = light.write(setup.PROPERTY_OUT_OF_SERVICE, application_boolean(False))
    record("back in service, Reliability follows the (healthy) lamp again - NO_FAULT_DETECTED, FAULT clear",
           acked(answer) and light.value(setup.PROPERTY_RELIABILITY) == NO_FAULT_DETECTED and
           fault_flag(light) is False)


def lamp_burns_out(args):
    example = setup.start_light(args, "light-lamp-burns-out", {"BLD_TEST_LAMP_BURNS_OUT": "1"})
    light = setup.Light(args)
    try:
        record("lamp hook: the example says the test hook is on",
               "TEST HOOK: BLD_TEST_LAMP_BURNS_OUT=1" in example.output())
        record("lamp hook, control: while the light is off, Reliability NO_FAULT_DETECTED and FAULT clear",
               light.value(setup.PROPERTY_RELIABILITY) == NO_FAULT_DETECTED and fault_flag(light) is False)
        answer = light.command(FADE_TO, target_level=60.0, fade_time=500)
        written_at = time.monotonic()
        wait_until(written_at, 0.5 + SLACK)
        record("lamp hook: switched on, the lamp burns out - Reliability LAMP_FAILURE",
               acked(answer) and light.value(setup.PROPERTY_RELIABILITY) == LAMP_FAILURE,
               f"read {light.value(setup.PROPERTY_RELIABILITY)}")
        record("lamp hook: Status_Flags FAULT is set (cl. 12.54.9)", fault_flag(light) is True,
               f"FAULT {fault_flag(light)}")
        record("lamp hook: the Lighting Output still carries out the command - Present_Value and "
               "Tracking_Value 60, In_Progress IDLE", light.state() == (60.0, 60.0, IDLE), f"read {light.state()}")
    finally:
        light.close()
        example.stop()
        if not all(wiretest.results.RESULTS):
            example.keep_log()


def main():
    args = setup.parser(__doc__).parse_args()
    example = setup.start_light(args)
    light = setup.Light(args)
    try:
        bad_commands(light)
        out_of_service(light)
        # Control for part 2: without the hook the lamp survives being switched on.
        light.write(setup.PROPERTY_PRESENT_VALUE, application_real(100.0), priority=16)
        time.sleep(SLACK)
        record("Control: without the test hook the lamp survives 100% - Reliability NO_FAULT_DETECTED",
               light.value(setup.PROPERTY_RELIABILITY) == NO_FAULT_DETECTED and fault_flag(light) is False)
    finally:
        light.close()
        example.stop()
        if not all(wiretest.results.RESULTS):
            example.keep_log()
    lamp_burns_out(args)
    return wiretest.summary()


if __name__ == "__main__":
    sys.exit(main())
