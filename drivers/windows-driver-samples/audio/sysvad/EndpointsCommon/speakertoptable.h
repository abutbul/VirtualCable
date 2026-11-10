/*++

Copyright (c) Microsoft Corporation All Rights Reserved

Module Name:

    speakertoptable.h

Abstract:

    Declaration of topology tables.

--*/

#ifndef _SYSVAD_SPEAKERTOPTABLE_H_
#define _SYSVAD_SPEAKERTOPTABLE_H_

#include "cablenames.h"

//=============================================================================
static
KSDATARANGE SpeakerTopoPinDataRangesBridge[] =
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
PKSDATARANGE SpeakerTopoPinDataRangePointersBridge[] =
{
  &SpeakerTopoPinDataRangesBridge[0]
};

//=============================================================================
// One pin table per cable: identical except for the bridge pin's Name GUID, which
// Windows uses (via the INF's MediaCategories entries) as the endpoint name.
#define SPEAKER_TOPO_MINIPORT_PINS(_EndpointName)                               \
{                                                                               \
  /* KSPIN_TOPO_WAVEOUT_SOURCE */                                               \
  {                                                                             \
    0, 0, 0,                                            /* InstanceCount */     \
    NULL,                                               /* AutomationTable */   \
    {                                                                           \
      0, NULL, 0, NULL,                                 /* Interfaces/Mediums */\
      SIZEOF_ARRAY(SpeakerTopoPinDataRangePointersBridge),                      \
      SpeakerTopoPinDataRangePointersBridge,                                    \
      KSPIN_DATAFLOW_IN,                                                        \
      KSPIN_COMMUNICATION_NONE,                                                 \
      &KSCATEGORY_AUDIO,                                /* Category */          \
      NULL,                                             /* Name */              \
      0                                                                         \
    }                                                                           \
  },                                                                            \
  /* KSPIN_TOPO_LINEOUT_DEST (bridge pin: names the endpoint) */                \
  {                                                                             \
    0, 0, 0,                                            /* InstanceCount */     \
    NULL,                                               /* AutomationTable */   \
    {                                                                           \
      0, NULL, 0, NULL,                                 /* Interfaces/Mediums */\
      SIZEOF_ARRAY(SpeakerTopoPinDataRangePointersBridge),                      \
      SpeakerTopoPinDataRangePointersBridge,                                    \
      KSPIN_DATAFLOW_OUT,                                                       \
      KSPIN_COMMUNICATION_NONE,                                                 \
      &KSNODETYPE_SPEAKER,                              /* Category */          \
      (_EndpointName),                                  /* Name */              \
      0                                                                         \
    }                                                                           \
  }                                                                             \
}

static PCPIN_DESCRIPTOR SpeakerTopoMiniportPins[]  = SPEAKER_TOPO_MINIPORT_PINS(&CABLE_A_INPUT_NAME);
static PCPIN_DESCRIPTOR SpeakerBTopoMiniportPins[] = SPEAKER_TOPO_MINIPORT_PINS(&CABLE_B_INPUT_NAME);
static PCPIN_DESCRIPTOR SpeakerCTopoMiniportPins[] = SPEAKER_TOPO_MINIPORT_PINS(&CABLE_C_INPUT_NAME);
static PCPIN_DESCRIPTOR SpeakerDTopoMiniportPins[] = SPEAKER_TOPO_MINIPORT_PINS(&CABLE_D_INPUT_NAME);

//=============================================================================
static
KSJACK_DESCRIPTION SpeakerJackDescBridge =
{
    KSAUDIO_SPEAKER_STEREO,
    0xB3C98C,               // Color spec for green
    eConnTypeUnknown,
    eGeoLocFront,
    eGenLocPrimaryBox,
    ePortConnIntegratedDevice,
    TRUE
};

// Only return a KSJACK_DESCRIPTION for the physical bridge pin.
static 
PKSJACK_DESCRIPTION SpeakerJackDescriptions[] =
{
    NULL,
    &SpeakerJackDescBridge
};

static SYSVAD_AUDIOPOSTURE_INFO SpeakerAudioPostureInfo = { TRUE };

// Only support property for the physical bridge pin.
static
PSYSVAD_AUDIOPOSTURE_INFO SpeakerAudioPostureInfoPointers[]
{
    NULL,
    &SpeakerAudioPostureInfo
};

//=============================================================================
static
PCCONNECTION_DESCRIPTOR SpeakerTopoMiniportConnections[] =
{
  //  FromNode,                     FromPin,                        ToNode,                      ToPin
  {   PCFILTER_NODE,                KSPIN_TOPO_WAVEOUT_SOURCE,      PCFILTER_NODE,               KSPIN_TOPO_LINEOUT_DEST}
};


//=============================================================================
static
PCPROPERTY_ITEM PropertiesSpeakerTopoFilter[] =
{
    {
        &KSPROPSETID_Jack,
        KSPROPERTY_JACK_DESCRIPTION,
        KSPROPERTY_TYPE_GET |
        KSPROPERTY_TYPE_BASICSUPPORT,
        PropertyHandler_SpeakerTopoFilter
    },
    {
        &KSPROPSETID_Jack,
        KSPROPERTY_JACK_DESCRIPTION2,
        KSPROPERTY_TYPE_GET |
        KSPROPERTY_TYPE_BASICSUPPORT,
        PropertyHandler_SpeakerTopoFilter
    },
    {
        &KSPROPSETID_Jack,
        KSPROPERTY_JACK_DESCRIPTION3,
        KSPROPERTY_TYPE_GET |
        KSPROPERTY_TYPE_BASICSUPPORT,
        PropertyHandler_SpeakerTopoFilter
    },
    {
        &KSPROPSETID_AudioResourceManagement,
        KSPROPERTY_AUDIORESOURCEMANAGEMENT_RESOURCEGROUP,
        KSPROPERTY_TYPE_SET,
        PropertyHandler_SpeakerTopoFilter
    }
    ,{
        &KSPROPSETID_AudioPosture,
        KSPROPERTY_AUDIOPOSTURE_ORIENTATION,
        KSPROPERTY_TYPE_SET |
        KSPROPERTY_TYPE_BASICSUPPORT,
        PropertyHandler_SpeakerTopoFilter
    }
};

DEFINE_PCAUTOMATION_TABLE_PROP(AutomationSpeakerTopoFilter, PropertiesSpeakerTopoFilter);

//=============================================================================
#define SPEAKER_TOPO_MINIPORT_FILTER_DESCRIPTOR(_Pins)                          \
{                                                                               \
  0,                                            /* Version */                   \
  &AutomationSpeakerTopoFilter,                 /* AutomationTable */           \
  sizeof(PCPIN_DESCRIPTOR),                     /* PinSize */                   \
  SIZEOF_ARRAY(_Pins),                          /* PinCount */                  \
  (_Pins),                                      /* Pins */                      \
  sizeof(PCNODE_DESCRIPTOR),                    /* NodeSize */                  \
  0,                                            /* NodeCount */                 \
  NULL,                                         /* Nodes */                     \
  SIZEOF_ARRAY(SpeakerTopoMiniportConnections), /* ConnectionCount */           \
  SpeakerTopoMiniportConnections,               /* Connections */               \
  0,                                            /* CategoryCount */             \
  NULL                                          /* Categories */                \
}

static PCFILTER_DESCRIPTOR SpeakerTopoMiniportFilterDescriptor  = SPEAKER_TOPO_MINIPORT_FILTER_DESCRIPTOR(SpeakerTopoMiniportPins);
static PCFILTER_DESCRIPTOR SpeakerBTopoMiniportFilterDescriptor = SPEAKER_TOPO_MINIPORT_FILTER_DESCRIPTOR(SpeakerBTopoMiniportPins);
static PCFILTER_DESCRIPTOR SpeakerCTopoMiniportFilterDescriptor = SPEAKER_TOPO_MINIPORT_FILTER_DESCRIPTOR(SpeakerCTopoMiniportPins);
static PCFILTER_DESCRIPTOR SpeakerDTopoMiniportFilterDescriptor = SPEAKER_TOPO_MINIPORT_FILTER_DESCRIPTOR(SpeakerDTopoMiniportPins);

#endif // _SYSVAD_SPEAKERTOPTABLE_H_

