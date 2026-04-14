"""
Dahua DSS Client - Interactive Python client for Dahua DSS Video Management System
"""

__version__ = "1.0.0"
__author__ = "Borja Lafuente"
__email__ = "borlafu@gmail.com"

from dahua_dss.client import DahuaDSSClient
from dahua_dss.models import (
    DssDeviceCategory,
    DssDeviceType,
    DssPlaybackRecordType,
    DssRecordSource,
    DssRecordType,
    DssStreamType,
)

__all__ = [
    "DahuaDSSClient",
    "DssDeviceCategory",
    "DssDeviceType",
    "DssPlaybackRecordType",
    "DssRecordSource",
    "DssRecordType",
    "DssStreamType",
]
