/*++

Copyright (c) Microsoft Corporation All Rights Reserved

Module Name:

    micintopotable.h

Abstract:

    Declaration of topology table for the mic (external: headphone)

--*/

#ifndef _SYSVAD_MICINTOPTABLE_H_
#define _SYSVAD_MICINTOPTABLE_H_

// Function declarations.
NTSTATUS
PropertyHandler_MicInTopoFilter( 
    _In_ PPCPROPERTY_REQUEST      PropertyRequest 
    );

#include "cablenames.h"

//=============================================================================
static
KSJACK_DESCRIPTION MicInJackDesc =
{
    KSAUDIO_SPEAKER_STEREO,
    JACKDESC_RGB(179, 201, 140),
    eConnTypeCombination,
    eGeoLocRear,
    eGenLocPrimaryBox,
    ePortConnJack,
    TRUE
};

//=============================================================================
static
KSDATARANGE MicInTopoPinDataRangesBridge[] =
{
 {
   sizeof(KSDATARANGE),
   0,
   0,
   0,
   STATICGUIDOF(KSDATAFORMAT_TYPE_AUDIO),
   STATICGUIDOF(KSDATAFORMAT_SUBTYPE_ANALOG),
   STATICGUIDOF(KSDATAFORMAT_SPECIFIER_NONE)
 }
};

//=============================================================================
static
PKSDATARANGE MicInTopoPinDataRangePointersBridge[] =
{
  &MicInTopoPinDataRangesBridge[0]
};

//=============================================================================
// One pin table per cable: identical except for the bridge (in) pin's Name GUID,
// which Windows uses (via the INF's MediaCategories entries) as the endpoint name.
#define MICIN_TOPO_MINIPORT_PINS(_EndpointName)                                 \
{                                                                               \
  /* KSPIN - topology filter in-pin (bridge pin: names the endpoint) */         \
  {                                                                             \
    0, 0, 0,                                            /* InstanceCount */     \
    NULL,                                               /* AutomationTable */   \
    {                                                                           \
      0, NULL, 0, NULL,                                 /* Interfaces/Mediums */\
      SIZEOF_ARRAY(MicInTopoPinDataRangePointersBridge),                        \
      MicInTopoPinDataRangePointersBridge,                                      \
      KSPIN_DATAFLOW_IN,                                                        \
      KSPIN_COMMUNICATION_NONE,                                                 \
      &KSNODETYPE_MICROPHONE,                           /* Category */          \
      (_EndpointName),                                  /* Name */              \
      0                                                                         \
    }                                                                           \
  },                                                                            \
  /* KSPIN - topology filter out-pin */                                         \
  {                                                                             \
    0, 0, 0,                                            /* InstanceCount */     \
    NULL,                                               /* AutomationTable */   \
    {                                                                           \
      0, NULL, 0, NULL,                                 /* Interfaces/Mediums */\
      SIZEOF_ARRAY(MicInTopoPinDataRangePointersBridge),                        \
      MicInTopoPinDataRangePointersBridge,                                      \
      KSPIN_DATAFLOW_OUT,                                                       \
      KSPIN_COMMUNICATION_NONE,                                                 \
      &KSCATEGORY_AUDIO,                                /* Category */          \
      NULL,                                             /* Name */              \
      0                                                                         \
    }                                                                           \
  }                                                                             \
}

static PCPIN_DESCRIPTOR MicInTopoMiniportPins[]  = MICIN_TOPO_MINIPORT_PINS(&CABLE_A_OUTPUT_NAME);
static PCPIN_DESCRIPTOR MicInBTopoMiniportPins[] = MICIN_TOPO_MINIPORT_PINS(&CABLE_B_OUTPUT_NAME);
static PCPIN_DESCRIPTOR MicInCTopoMiniportPins[] = MICIN_TOPO_MINIPORT_PINS(&CABLE_C_OUTPUT_NAME);
static PCPIN_DESCRIPTOR MicInDTopoMiniportPins[] = MICIN_TOPO_MINIPORT_PINS(&CABLE_D_OUTPUT_NAME);

//=============================================================================
// Only return a KSJACK_DESCRIPTION for the physical bridge pin.
static 
PKSJACK_DESCRIPTION MicInJackDescriptions[] =
{
    &MicInJackDesc,
    NULL
};

//=============================================================================
static
PCPROPERTY_ITEM MicInPropertiesVolume[] =
{
  {
    &KSPROPSETID_Audio,
    KSPROPERTY_AUDIO_VOLUMELEVEL,
    KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_SET | KSPROPERTY_TYPE_BASICSUPPORT,
    PropertyHandler_Topology
  }
};

DEFINE_PCAUTOMATION_TABLE_PROP(AutomationMicInVolume, MicInPropertiesVolume);

//=============================================================================
static
PCPROPERTY_ITEM MicInPropertiesMute[] =
{
  {
    &KSPROPSETID_Audio,
    KSPROPERTY_AUDIO_MUTE,
    KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_SET | KSPROPERTY_TYPE_BASICSUPPORT,
    PropertyHandler_Topology
  }
};

DEFINE_PCAUTOMATION_TABLE_PROP(AutomationMicInMute, MicInPropertiesMute);

//=============================================================================
static
PCPROPERTY_ITEM MicInPropertiesPeakMeter[] =
{
  {
    &KSPROPSETID_Audio,
    KSPROPERTY_AUDIO_PEAKMETER2,
    KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_BASICSUPPORT,
    PropertyHandler_Topology
  },
  {
    &KSPROPSETID_Audio,
    KSPROPERTY_AUDIO_CPU_RESOURCES,
    KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_BASICSUPPORT,
    PropertyHandler_Topology
  }
};

DEFINE_PCAUTOMATION_TABLE_PROP(AutomationMicInPeakMeter, MicInPropertiesPeakMeter);

//=============================================================================
static
PCNODE_DESCRIPTOR MicInTopologyNodes[] =
{
  // KSNODE_TOPO_VOLUME
  {
    0,                          // Flags
    &AutomationMicInVolume,     // AutomationTable
    &KSNODETYPE_VOLUME,         // Type
    &KSAUDFNAME_MIC_VOLUME      // Name
  },
  // KSNODE_TOPO_MUTE
  {
    0,                          // Flags
    &AutomationMicInMute,       // AutomationTable
    &KSNODETYPE_MUTE,           // Type
    &KSAUDFNAME_MIC_MUTE        // Name
  },
  // KSNODE_TOPO_PEAKMETER
  {
    0,                          // Flags
    &AutomationMicInPeakMeter,  // AutomationTable
    &KSNODETYPE_PEAKMETER,      // Type
    &KSAUDFNAME_PEAKMETER       // Name
  }
};

C_ASSERT( KSNODE_TOPO_VOLUME  == 0 );
C_ASSERT( KSNODE_TOPO_MUTE    == 1 );
C_ASSERT( KSNODE_TOPO_PEAKMETER == 2 );

//=============================================================================
static
PCCONNECTION_DESCRIPTOR MicInMiniportConnections[] =
{
    //  FromNode,                 FromPin,                    ToNode,                 ToPin
    {   PCFILTER_NODE,            KSPIN_TOPO_MIC_ELEMENTS,    KSNODE_TOPO_VOLUME,     1 },
    {   KSNODE_TOPO_VOLUME,       0,                          KSNODE_TOPO_MUTE,       1 },
    {   KSNODE_TOPO_MUTE,         0,                          KSNODE_TOPO_PEAKMETER,  1 },
    {   KSNODE_TOPO_PEAKMETER,    0,                          PCFILTER_NODE,          KSPIN_TOPO_BRIDGE }
};


//=============================================================================
static
PCPROPERTY_ITEM MicInPropertiesTopoFilter[] =
{
    {
        &KSPROPSETID_Jack,
        KSPROPERTY_JACK_DESCRIPTION,
        KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_BASICSUPPORT,
        PropertyHandler_MicInTopoFilter
    },
    {
        &KSPROPSETID_Jack,
        KSPROPERTY_JACK_DESCRIPTION2,
        KSPROPERTY_TYPE_GET | KSPROPERTY_TYPE_BASICSUPPORT,
        PropertyHandler_MicInTopoFilter
    }
};

DEFINE_PCAUTOMATION_TABLE_PROP(AutomationMicInTopoFilter, MicInPropertiesTopoFilter);

//=============================================================================
#define MICIN_TOPO_MINIPORT_FILTER_DESCRIPTOR(_Pins)                            \
{                                                                               \
  0,                                        /* Version */                       \
  &AutomationMicInTopoFilter,               /* AutomationTable */               \
  sizeof(PCPIN_DESCRIPTOR),                 /* PinSize */                       \
  SIZEOF_ARRAY(_Pins),                      /* PinCount */                      \
  (_Pins),                                  /* Pins */                          \
  sizeof(PCNODE_DESCRIPTOR),                /* NodeSize */                      \
  SIZEOF_ARRAY(MicInTopologyNodes),         /* NodeCount */                     \
  MicInTopologyNodes,                       /* Nodes */                         \
  SIZEOF_ARRAY(MicInMiniportConnections),   /* ConnectionCount */               \
  MicInMiniportConnections,                 /* Connections */                   \
  0,                                        /* CategoryCount */                 \
  NULL                                      /* Categories */                    \
}

static PCFILTER_DESCRIPTOR MicInTopoMiniportFilterDescriptor  = MICIN_TOPO_MINIPORT_FILTER_DESCRIPTOR(MicInTopoMiniportPins);
static PCFILTER_DESCRIPTOR MicInBTopoMiniportFilterDescriptor = MICIN_TOPO_MINIPORT_FILTER_DESCRIPTOR(MicInBTopoMiniportPins);
static PCFILTER_DESCRIPTOR MicInCTopoMiniportFilterDescriptor = MICIN_TOPO_MINIPORT_FILTER_DESCRIPTOR(MicInCTopoMiniportPins);
static PCFILTER_DESCRIPTOR MicInDTopoMiniportFilterDescriptor = MICIN_TOPO_MINIPORT_FILTER_DESCRIPTOR(MicInDTopoMiniportPins);

#endif // _SYSVAD_MICINTOPTABLE_H_

