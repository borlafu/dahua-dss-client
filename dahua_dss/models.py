"""Dahua DSS domain enums"""

from enum import Enum


class DssDeviceCategory(str, Enum):
    Encoder = "1"


class DssDeviceType(str, Enum):
    DvrXvr = "1"
    Ipc = "2"
    Nvs = "3"
    MdvrMxvrMnvr = "5"
    Nvr = "6"
    Mpt = "9"
    Evs = "10"
    ThermalCamera = "26"
    IvssDivd = "43"
    Eec = "97"


class DssStreamType(str, Enum):
    Main = "1"
    Sub = "2"


class DssRecordSource(str, Enum):
    Device = "2"
    Center = "3"


class DssRecordType(str, Enum):
    All = "0"
    Manual = "1"
    Alarm = "2"
    DynamicMonitoring = "3"
    VideoLoss = "4"
    VideoTampering = "5"
    Scheduled = "6"
    AllWeather = "7"
    FileConversion = "8"


class DssPlaybackRecordType(str, Enum):
    General = "1"
    Alarm = "2"
