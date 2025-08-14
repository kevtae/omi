"""
Omi Python SDK

A Python SDK for connecting to Omi wearable devices over Bluetooth,
decoding Opus-encoded audio, and transcribing it in real time.
"""

__version__ = "0.1.0"

from .bluetooth import print_devices, listen_to_omi, listen_to_omi_with_button
from .button import ButtonHandler, ButtonState, RecordingState
from .decoder import OmiOpusDecoder
from .feedback import RecordingFeedback
from .transcribe import transcribe

__all__ = [
    "print_devices",
    "listen_to_omi",
    "listen_to_omi_with_button",
    "ButtonHandler",
    "ButtonState", 
    "RecordingState",
    "OmiOpusDecoder", 
    "RecordingFeedback",
    "transcribe",
    "__version__",
]