# BACnet Protocol Implementation Conformance Statement (PICS)

For the **BACnet B-LD (Lighting Device) C++ example** -
see [README.md](../README.md).

> This is the PICS **for the example as shipped**. It describes a tutorial
> device announcing itself as a Chipkin demo, not a product. When you turn this
> example into your own device, this document is one of the things you rewrite:
> the vendor, model and version rows all come from the
> `CHANGE ALL OF THIS BEFORE YOU SHIP` block at the top of `main.cpp`. The
> example has **not** been submitted for BTL certification.

## 1. Product description

| | |
|---|---|
| **Vendor Name** | Chipkin Automation Systems |
| **Vendor Identifier** | 389 |
| **Product Name** | CAS BACnet Stack Example - B-LD |
| **Product Model Number** | CAS BACnet Stack Example - B-LD |
| **Application Software Version** | 1.2.0 |
| **Firmware Revision** | 6.0.23.0 (the CAS BACnet Stack version) |
| **BACnet Protocol Version** | 1 |
| **BACnet Protocol Revision** | 30 |

**Product Description:** a BACnet/IP luminaire built on the CAS BACnet Stack. It
presents one commandable Lighting Output whose level is driven by both a
16-slot Priority_Array and the constructed `Lighting_Command` SEQUENCE. Every
operation of Table 12-67 is carried out over time - fades over their fade
time, ramps at their ramp rate, warns wait out `Egress_Time` - with
`Tracking_Value`, `In_Progress` and `Egress_Active` reporting it; the lamp and
dimming driver are a labelled Simulation. Plus DeviceCommunicationControl and
local TimeSynchronization. It answers ReadProperty and WriteProperty for every
required property of every object, and is discoverable by Who-Is / I-Am and
Who-Has / I-Have. It is a tutorial for implementers of the B-LD profile.

## 2. BACnet standardized device profile (Annex L)

**B-LD - BACnet Lighting Device.**

This device claims exactly one profile. Because the B-LD requirements are a
superset of B-GENERAL's, a conformant B-LD device also satisfies **B-GENERAL**
(Annex L.8); that is subsumption, not a second claim.

## 3. BIBBs supported (Annex K)

| BIBB | Description |
|---|---|
| DS-RP-B | Data Sharing - ReadProperty - B |
| DS-WP-B | Data Sharing - WriteProperty - B |
| DS-LO-B | Data Sharing - Lighting Output - B |
| DM-DDB-B | Device Management - Dynamic Device Binding - B |
| DM-DOB-B | Device Management - Dynamic Object Binding - B |
| DM-DCC-B | Device Management - DeviceCommunicationControl - B |
| DM-TS-B | Device Management - TimeSynchronization - B |

The profile allows **DS-BLO-B *or* DS-LO-B** (a Binary Lighting Output would
also satisfy it); this example implements DS-LO-B, the dimmable Lighting
Output, because it is the richer of the two and the one that carries
`Lighting_Command`. The profile also allows **DM-TS-B *or* DM-UTC-B**; this
example does local TimeSync only - `SERVICE_UTC_TIME_SYNCHRONIZATION` is never
enabled, and a UTCTimeSynchronization request is rejected by the stack itself
before it reaches the application.

No other BIBBs are supported. In particular this device does **not** support
DS-RPM-B (ReadPropertyMultiple), DS-COV-B, any alarm and event (AE-*) BIBB,
scheduling (SCHED-*), or trending (T-*).

## 4. Application services supported

| Service | Initiate | Execute |
|---|:---:|:---:|
| ReadProperty | no | **yes** |
| WriteProperty | no | **yes** |
| Who-Is | no | **yes** |
| I-Am | **yes** | - |
| Who-Has | no | **yes** |
| I-Have | **yes** | - |
| DeviceCommunicationControl | no | **yes** |
| TimeSynchronization | no | **yes** |

An unsolicited I-Am is broadcast to the local subnet at start-up, as well as in
response to Who-Is.

Any other confirmed service - including ReadPropertyMultiple,
UTCTimeSynchronization, and any COV or alarm/event service - is rejected. That
rejection is part of the profile boundary, not a limitation to work around.

## 5. Segmentation capability

Segmentation is **supported in both directions**
(`Segmentation_Supported` = `segmented-both`), by the stack: at `6.x` @
`64b2cfac5` the customer build compiles `STACK_OPTION_SEGMENTATION` in (stack
#2992), and this example keeps the stack's defaults for `Max_Segments_Accepted`
and `APDU_Segment_Timeout`. Table 12-13 footnote 1: "These properties are
required if, and shall be present only if, segmentation of any kind is
supported" - they are not rows in section 11 because its generator lists only
unconditionally required properties. `Max_APDU_Length_Accepted` is 1476 octets,
the BACnet/IP maximum. (At the previous pin, `abd4cee1`, this example answered
`no-segmentation`.)

## 6. Standard object types supported

No object is dynamically creatable or deletable.

| Object type | Instance | Object_Name | Optional properties supported |
|---|:---:|---|---|
| Device | 389016 | Chipkin Example B-LD | Description |
| Lighting Output | 1 | Jade | Reliability |
| Network Port | 1 | Vermilion | - |

These are exactly the B-LD profile's objects (Annex L.11.2), plus the Device and
Network Port every device has. (Up to v1.1.3 the example also carried an Analog,
Binary and Multi-state Input and Output inherited from the B-ASC example.)

On the Lighting Output, writable: `Present_Value` (commandable, via its
Priority_Array, including the special values -1.0 to -7.0 of Table 12-65),
`Lighting_Command`, `Default_Fade_Time` (100 to 86400000 ms),
`Default_Ramp_Rate` (0.1 to 100 %/s), `Default_Step_Increment` (0.1 to 100 %),
`Egress_Time`, `Out_Of_Service`, and `Reliability` while `Out_Of_Service` is
TRUE (cl. 12.54.12). A value out of range is refused with PROPERTY /
VALUE_OUT_OF_RANGE. No property of any other object is writable.

`Lighting_Command` supports every BACnetLightingOperation of Table 12-67 (fadeTo,
rampTo, stepUp, stepDown, stepOn, stepOff, warn, warnOff, warnRelinquish, stop,
restoreOn, defaultOn, toggleRestore, toggleDefault); `none` and proprietary
operations are refused. The object has no `Transition` property, so a direct
write or relinquish takes effect at once (cl. 12.54.19); `Blink_Warn_Enable` is
TRUE; `Default_On_Value` is 100.0 %.

The device instance is configurable at run time with `--deviceID` (BACnet
requires the device instance to be configurable).

## 7. Data link layer options

**BACnet/IP (Annex J)**, UDP port 47808 (0xBAC0) by default, configurable at run
time with `--port`.

BBMD is not supported, Foreign Device registration is not supported, and
BACnet/SC, MS/TP, Ethernet (Annex H) and PTP are not supported.

## 8. Device address binding

Static device binding is **not supported**. The device answers Who-Is/Who-Has
and does not initiate any confirmed request, so it never needs to bind a peer.

## 9. Networking options

None. The device is not a router, not a BBMD, and does not register as a foreign
device.

## 10. Character sets supported

UTF-8 (ANSI X3.4). Supporting a character set does not imply the device can
handle data in all character sets.

## 11. Objects and properties

<!-- OBJECTS-PROPERTIES:BEGIN (generated by tools/gen-objects-properties.py from docs/objects.json - do not edit here) -->
Every object this example creates, and every REQUIRED property of each (per ANSI/ASHRAE 135-2024 clause 12 and the stack's `docs/property-profile-reference.md`), plus the optional properties the example turns on. **Served by** says who answers a ReadProperty: the **stack** generates it, or the **app** serves it from a `GetProperty*` callback in `main.cpp`. A ⚠ row is a required property the app does not serve and the stack would fill with a default - that is a defect, not a feature.

### Device 389016 "Chipkin Example B-LD" - the device itself; the instance is configurable with --deviceID. The stack rows are device-wide facts only the stack knows - the protocol version and revision it implements, the services and object types it was configured with, the live object list and address-binding table. The accepted rows are the stack's configured defaults for APDU limits, segmentation, system status and database revision; an application that answered them from its own constants could contradict the stack, so this example does not. Local_Date and Local_Time (optional Device properties) have GetPropertyDate/GetPropertyTime callbacks in main.cpp, but nothing calls SetPropertyEnabled for either - so they are never in the object's enabled-property list and the stack answers unknown-property before either callback is reached. See TUTORIAL.md for the details

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| System_Status | BACnetDeviceStatus | stack default, accepted (Generic Enumerated default: `0`) | no |
| Vendor_Name | CharacterString | app | no |
| Vendor_Identifier | Unsigned16 | app | no |
| Model_Name | CharacterString | app | no |
| Firmware_Revision | CharacterString | app | no |
| Application_Software_Version | CharacterString | app | no |
| Description *(optional, enabled)* | CharacterString | app | no |
| Protocol_Version | Unsigned | stack | no |
| Protocol_Revision | Unsigned | stack | no |
| Protocol_Services_Supported | BACnetServicesSupported | stack | no |
| Protocol_Object_Types_Supported | BACnetObjectTypesSupported | stack | no |
| Object_List | BACnetARRAY[N] of BACnetObjectIdentifier | stack | no |
| Max_APDU_Length_Accepted | Unsigned | stack default, accepted (`CAS_BACNET_DEVICE_DEFAULT_MAX_APDU_LENGTH_ACCEPTED`) | no |
| Segmentation_Supported | BACnetSegmentation | stack default, accepted (`BACnetSegmentation::segmentedBoth` with `STACK_OPTION_SEGME) | no |
| APDU_Timeout | Unsigned | stack default, accepted (`CAS_BACNET_DEVICE_DEFAULT_APDU_TIMEOUT`) | no |
| Number_Of_APDU_Retries | Unsigned | stack default, accepted (`CAS_BACNET_DEVICE_DEFAULT_NUMBER_OF_APDU_RETRIES`) | no |
| Device_Address_Binding | BACnetLIST of BACnetAddressBinding | stack | no |
| Database_Revision | Unsigned | stack default, accepted (Generic UnsignedInteger default: `0`) | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

### Lighting Output 1 "Jade" - REAL 0-100%; commandable via a 16-slot Priority_Array (WriteProperty/DS-WP-B) AND via the typed Lighting_Command SEQUENCE (DS-LO-B). This is B-LD's canonical F-LIGHT object. The app's lighting engine (main.cpp section 1b) runs every Table 12-67 operation over time: Present_Value is the target, Tracking_Value the level being driven, In_Progress fadeActive/rampActive while it moves, Egress_Active TRUE during a warn's egress time. Reliability (optional, enabled) reports lampFailure from the lamp Simulation and is writable only while Out_Of_Service is TRUE (cl. 12.54.12); the dimming defaults and Egress_Time are writable, range-checked. Last_On_Value and Default_On_Value (required in 135-2024, cl. 12.54.44/45) are served by the app but not rows here because the stack's property-profile reference at this pin does not list them; Current_Command_Priority and Property_List are served by the stack

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Present_Value | Real | stack | yes |
| Tracking_Value | Real | app | no |
| Lighting_Command | BACnetLightingCommand | app | yes |
| In_Progress | BACnetLightingInProgress | app | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Reliability *(optional, enabled)* | BACnetReliability | app | yes |
| Out_Of_Service | Boolean | app | yes |
| Blink_Warn_Enable | Boolean | app | no |
| Egress_Time | Unsigned | app | yes |
| Egress_Active | Boolean | app | no |
| Default_Fade_Time | Unsigned | app | yes |
| Default_Ramp_Rate | Real | app | yes |
| Default_Step_Increment | Real | app | yes |
| Priority_Array | BACnetARRAY[16] of BACnetOptionalReal | stack | no |
| Relinquish_Default | Real | app | no |
| Lighting_Command_Default_Priority | Unsigned | app | no |

### Network Port 1 "Vermilion" - BACnet/IP; Network_Type and Protocol_Level are set from BACnetStack_AddNetworkPortObject()'s arguments (IPv4, BACnet Application) at start-up, not a GetProperty callback like the object's other app-served rows; Changes_Pending is likewise computed and answered natively by the stack's Network Port object. Reliability has no fault condition this example detects, so it is accepted at the generic default (normal)

| Property | Datatype | Served by | Writable |
|---|---|---|:---:|
| Object_Identifier | BACnetObjectIdentifier | stack | no |
| Object_Name | CharacterString | app | no |
| Object_Type | BACnetObjectType | stack | no |
| Status_Flags | BACnetStatusFlags | stack | no |
| Reliability | BACnetReliability | stack default, accepted (Generic Enumerated default: `0`) | no |
| Out_Of_Service | Boolean | app | no |
| Network_Type | BACnetNetworkType | app | no |
| Protocol_Level | BACnetProtocolLevel | app | no |
| Changes_Pending | Boolean | app | no |
| Property_List | BACnetARRAY[N] of BACnetPropertyIdentifier | stack | no |

<!-- OBJECTS-PROPERTIES:END -->

## 12. References

- ANSI/ASHRAE Standard 135-2024, Annex A (PICS template), Annex K (BIBBs),
  Annex L (device profiles), Clause 12 (object types).
- [README.md](../README.md) - what this example is and how to build it.
- [TUTORIAL.md](../TUTORIAL.md) - how to extend it, and how to keep this
  document honest when you do.
