"""
Button service handling for Omi wearable devices.

This module provides functionality to detect and handle button press events
from Omi devices over Bluetooth, enabling features like push-to-talk recording.
"""

import struct
from enum import IntEnum
from typing import Callable, Optional, List


# Button service and characteristic UUIDs
BUTTON_SERVICE_UUID = "23ba7924-0000-1000-7450-346eac492e92"
BUTTON_TRIGGER_CHARACTERISTIC_UUID = "23ba7925-0000-1000-7450-346eac492e92"

# Speaker/haptic service and characteristic UUIDs
SPEAKER_SERVICE_UUID = "cab1ab95-2ea5-4f4d-bb56-874b72cfc984"
SPEAKER_CHARACTERISTIC_UUID = "cab1ab96-2ea5-4f4d-bb56-874b72cfc984"


class ButtonState(IntEnum):
    """Button states reported by the Omi device."""
    IDLE = 0
    LONG_PRESS_START = 3
    LONG_PRESS_RELEASE = 5


class RecordingState(IntEnum):
    """Recording states for managing audio capture."""
    IDLE = 0
    RECORDING = 1


class ButtonHandler:
    """
    Handles button events from Omi devices and manages recording state.
    
    This class processes button notifications and manages a toggle-based
    recording system where long presses start and stop recording.
    
    Button Press Guidelines:
    - Hold button for AT LEAST 1 second (firmware requirement)
    - Recommended: Hold for 1.5-2 seconds for reliability
    - Wait 0.5 seconds between presses
    - Ensure stable Bluetooth connection
    """
    
    def __init__(
        self,
        on_recording_start: Optional[Callable[[], None]] = None,
        on_recording_stop: Optional[Callable[[], None]] = None,
        on_button_event: Optional[Callable[[ButtonState], None]] = None,
        haptic_callback: Optional[Callable[[int], None]] = None
    ):
        """
        Initialize the button handler.
        
        Args:
            on_recording_start: Callback when recording starts
            on_recording_stop: Callback when recording stops
            on_button_event: Callback for raw button events
            haptic_callback: Callback to trigger haptic feedback (level 1-3)
        """
        self.recording_state = RecordingState.IDLE
        self.on_recording_start = on_recording_start
        self.on_recording_stop = on_recording_stop
        self.on_button_event = on_button_event
        self.haptic_callback = haptic_callback
        self._toggle_count = 0
    
    def process_button_data(self, data: bytes) -> Optional[ButtonState]:
        """
        Process raw button data from the Bluetooth characteristic.
        
        Args:
            data: Raw bytes from the button characteristic
            
        Returns:
            The parsed ButtonState or None if parsing fails
        """
        if len(data) < 4:
            print(f"Button data too short: {len(data)} bytes")
            return None
        
        # Button state is in first 4 bytes, little endian (no reversal needed)
        # The data format appears to be: [state, 0, 0, 0, ...additional bytes...]
        state_value = struct.unpack('<I', data[:4])[0]
        print(f"Parsed button state value: {state_value}")
        
        try:
            button_state = ButtonState(state_value)
        except ValueError:
            # Unknown state value - let's see all possible values
            print(f"Unknown button state: {state_value} (raw data: {data.hex()})")
            return None
        
        # Check for rapid duplicate notifications within a short time window
        # Only filter true duplicates (same state within 100ms), not legitimate repeated presses
        import time
        current_time = time.time()
        
        if hasattr(self, '_last_button_state') and hasattr(self, '_last_button_time'):
            time_diff = current_time - self._last_button_time
            if self._last_button_state == button_state and time_diff < 0.1:  # 100ms window
                print(f"⚠️  Rapid duplicate button state ignored: {button_state} (within {time_diff:.3f}s)")
                return button_state
            elif self._last_button_state == button_state:
                print(f"✅ Same state but after {time_diff:.2f}s - processing as new press")
        
        self._last_button_state = button_state
        self._last_button_time = current_time
        
        # Call raw event handler if provided
        if self.on_button_event:
            self.on_button_event(button_state)
        
        # Handle recording toggle on long press START (more reliable than RELEASE)
        # Users get immediate feedback and can retry if no vibration/audio
        if button_state == ButtonState.LONG_PRESS_START:
            print(f"✅ Long press detected! Toggling recording - Current state: {self.recording_state}")
            # Trigger haptic feedback immediately for user confirmation
            if self.haptic_callback:
                haptic_level = 1  # 20ms vibration (level 1=20ms, 2=50ms, 3=500ms)
                self.haptic_callback(haptic_level)
            self._toggle_recording()
        elif button_state == ButtonState.LONG_PRESS_RELEASE:
            print(f"🔵 Long press released - toggle already happened on START")
        
        return button_state
    
    def _toggle_recording(self) -> None:
        """Toggle the recording state and trigger appropriate callbacks."""
        if self.recording_state == RecordingState.IDLE:
            self.recording_state = RecordingState.RECORDING
            self._toggle_count += 1
            print(f"🔴 Recording started (toggle #{self._toggle_count})")
            if self.on_recording_start:
                self.on_recording_start()
        else:
            self.recording_state = RecordingState.IDLE
            print(f"⏹️ Recording stopped (toggle #{self._toggle_count})")
            if self.on_recording_stop:
                self.on_recording_stop()
    
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.recording_state == RecordingState.RECORDING
    
    def reset(self) -> None:
        """Reset the handler to initial state."""
        self.recording_state = RecordingState.IDLE
        self._toggle_count = 0


def parse_button_state(data: List[int]) -> Optional[ButtonState]:
    """
    Utility function to parse button state from raw data.
    
    Args:
        data: List of integers from Bluetooth notification
        
    Returns:
        Parsed ButtonState or None
    """
    if len(data) < 4:
        return None
    
    # Convert list to bytes and parse
    data_bytes = bytes(data)
    state_bytes = data_bytes[:4][::-1]
    state_value = struct.unpack('>I', state_bytes)[0]
    
    try:
        return ButtonState(state_value)
    except ValueError:
        return None