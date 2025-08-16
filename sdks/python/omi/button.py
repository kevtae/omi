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
            haptic_callback: Callback to trigger basic haptic feedback (level 1-3)
                           Note: Enhanced start/stop haptic patterns are handled automatically
        """
        self.recording_state = RecordingState.IDLE
        self.on_recording_start = on_recording_start
        self.on_recording_stop = on_recording_stop
        self.on_button_event = on_button_event
        self.haptic_callback = haptic_callback
        self._enhanced_haptic_callback = None  # For enhanced start/stop patterns
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
            return None
        
        # Button state is in first 4 bytes, little endian (no reversal needed)
        # The data format appears to be: [state, 0, 0, 0, ...additional bytes...]
        state_value = struct.unpack('<I', data[:4])[0]
        
        try:
            button_state = ButtonState(state_value)
        except ValueError:
            return None
        
        # DUPLICATE FILTERING DISABLED - Was causing legitimate button presses to be filtered out
        # The firmware fix ensures reliable button events, so aggressive filtering is no longer needed
        import time
        current_time = time.time()
        
        # Keep tracking variables for potential future use but don't filter
        self._last_button_state = button_state
        self._last_button_time = current_time
        
        # Call raw event handler if provided
        if self.on_button_event:
            self.on_button_event(button_state)
        
        # TODO: REMOVE AFTER FIRMWARE UPDATE - FIRMWARE BUG WORKAROUND: Handle both START and RELEASE events intelligently
        if button_state == ButtonState.LONG_PRESS_START:
            # self._last_start_time = current_time  # TODO: REMOVE AFTER FIRMWARE UPDATE
            self._toggle_recording()
            
        elif button_state == ButtonState.LONG_PRESS_RELEASE:
            pass  # Release events are ignored with fallback disabled
        
        return button_state
    

    def _toggle_recording(self) -> None:
        """Toggle the recording state and trigger appropriate callbacks."""
        if self.recording_state == RecordingState.IDLE:
            self.recording_state = RecordingState.RECORDING
            self._toggle_count += 1
            
            # Enhanced haptic for recording start
            if self._enhanced_haptic_callback:
                self._enhanced_haptic_callback("start")
            elif self.haptic_callback:
                self.haptic_callback(1)  # Fallback to basic haptic
            
            if self.on_recording_start:
                self.on_recording_start()
        else:
            self.recording_state = RecordingState.IDLE
            
            # Enhanced haptic for recording stop
            if self._enhanced_haptic_callback:
                self._enhanced_haptic_callback("stop")
            elif self.haptic_callback:
                self.haptic_callback(1)  # Fallback to basic haptic
                
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