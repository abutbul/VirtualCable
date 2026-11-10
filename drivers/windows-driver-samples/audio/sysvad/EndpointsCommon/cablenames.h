/*++

Module Name:

    cablenames.h

Abstract:

    Name GUIDs for the virtual cable endpoints. Each topology filter's bridge pin
    reports one of these through KSPROPERTY_PIN_NAME; the INF maps each GUID under
    the device's MediaCategories key to the endpoint name shown by Windows
    ("CABLE-A Input", "CABLE-A Output", ...). Keep in sync with
    ComponentizedAudioSample.inx ([Strings] CableXInputNameGUID / CableXOutputNameGUID).

--*/

#ifndef _SYSVAD_CABLENAMES_H_
#define _SYSVAD_CABLENAMES_H_

// {fe85318b-5d33-4502-a777-e3dd675e4eb7}
static const GUID CABLE_A_INPUT_NAME  = { 0xfe85318b, 0x5d33, 0x4502, { 0xa7, 0x77, 0xe3, 0xdd, 0x67, 0x5e, 0x4e, 0xb7 } };
// {67a12516-64d8-4caf-8252-5a6f43d2f99e}
static const GUID CABLE_B_INPUT_NAME  = { 0x67a12516, 0x64d8, 0x4caf, { 0x82, 0x52, 0x5a, 0x6f, 0x43, 0xd2, 0xf9, 0x9e } };
// {7b589037-81e9-4558-afaf-207429f726e2}
static const GUID CABLE_C_INPUT_NAME  = { 0x7b589037, 0x81e9, 0x4558, { 0xaf, 0xaf, 0x20, 0x74, 0x29, 0xf7, 0x26, 0xe2 } };
// {96a7af25-724b-405a-ab6d-6e07071a0c0a}
static const GUID CABLE_D_INPUT_NAME  = { 0x96a7af25, 0x724b, 0x405a, { 0xab, 0x6d, 0x6e, 0x07, 0x07, 0x1a, 0x0c, 0x0a } };

// {95b5db96-5a17-4e2f-9efb-71d4b507a5dc}
static const GUID CABLE_A_OUTPUT_NAME = { 0x95b5db96, 0x5a17, 0x4e2f, { 0x9e, 0xfb, 0x71, 0xd4, 0xb5, 0x07, 0xa5, 0xdc } };
// {350ffefa-ddfb-4a34-b326-2ab4cacc97af}
static const GUID CABLE_B_OUTPUT_NAME = { 0x350ffefa, 0xddfb, 0x4a34, { 0xb3, 0x26, 0x2a, 0xb4, 0xca, 0xcc, 0x97, 0xaf } };
// {f2916824-07c4-4a92-958d-e26dfb9f2952}
static const GUID CABLE_C_OUTPUT_NAME = { 0xf2916824, 0x07c4, 0x4a92, { 0x95, 0x8d, 0xe2, 0x6d, 0xfb, 0x9f, 0x29, 0x52 } };
// {ffc5bf14-da5c-4027-a549-7f2ee76f1cc2}
static const GUID CABLE_D_OUTPUT_NAME = { 0xffc5bf14, 0xda5c, 0x4027, { 0xa5, 0x49, 0x7f, 0x2e, 0xe7, 0x6f, 0x1c, 0xc2 } };

#endif // _SYSVAD_CABLENAMES_H_
