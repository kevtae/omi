"""
Example demonstrating button-controlled recording with the Omi device.

This example shows how to:
1. Connect to an Omi device with button support
2. Toggle recording on/off with long press
3. Provide audio feedback for recording states
4. Handle button events for custom behaviors

Button States:
- State 3: Long press started (button held down)
- State 5: Long press released
- First long press: Starts recording
- Second long press: Stops recording
"""

import asyncio
import os
from typing import Any, Optional
from asyncio import Queue
from datetime import datetime

from omi.bluetooth import listen_to_omi_with_button
from omi.button import ButtonHandler, ButtonState
from omi.decoder import OmiOpusDecoder
from omi.transcribe import transcribe
from omi.feedback import RecordingFeedback, AudioFeedback


# Configuration - Replace with your device's MAC address
OMI_MAC = "C9DDDACB-CA1E-CDD6-7A17-59A2A5303CDA"  # Use omi-scan to find this
AUDIO_CHAR_UUID = "19B10001-E8F2-537E-4F6C-D104768A1214"


class RecordingSession:
    """Manages a recording session with button control."""
    
    def __init__(self, api_key: str):
        """
        Initialize recording session.
        
        Args:
            api_key: Deepgram API key for transcription
        """
        self.api_key = api_key
        self.audio_queue: Queue[bytes] = Queue()
        self.decoder = OmiOpusDecoder()
        self.is_recording = False
        self.recording_start_time: Optional[datetime] = None
        self.audio_bytes_received = 0
        
        # Initialize feedback system
        self.audio_feedback = AudioFeedback(enabled=True)
        self.recording_feedback = RecordingFeedback(self.audio_feedback)
        
        # Initialize button handler with callbacks
        self.button_handler = ButtonHandler(
            on_recording_start=self._on_recording_start,
            on_recording_stop=self._on_recording_stop,
            on_button_event=self._on_button_event
        )
    
    def _on_recording_start(self) -> None:
        """Handle recording start event."""
        self.is_recording = True
        self.recording_start_time = datetime.now()
        self.audio_bytes_received = 0
        self.recording_feedback.on_recording_start()
        print(f"📍 Recording session started at {self.recording_start_time.strftime('%H:%M:%S')}")
    
    def _on_recording_stop(self) -> None:
        """Handle recording stop event."""
        self.is_recording = False
        if self.recording_start_time:
            duration = (datetime.now() - self.recording_start_time).total_seconds()
            print(f"📊 Recording session ended - Duration: {duration:.1f}s, Bytes: {self.audio_bytes_received}")
        self.recording_feedback.on_recording_stop()
        self.recording_start_time = None
    
    def _on_button_event(self, state: ButtonState) -> None:
        """
        Handle raw button events for debugging or custom behaviors.
        
        Args:
            state: The button state that was detected
        """
        state_names = {
            ButtonState.IDLE: "IDLE",
            ButtonState.LONG_PRESS_START: "LONG_PRESS_START",
            ButtonState.LONG_PRESS_RELEASE: "LONG_PRESS_RELEASE"
        }
        print(f"🔘 Button event: {state_names.get(state, f'UNKNOWN({state})')}")
    
    def handle_audio_data(self, sender: Any, data: bytes) -> None:
        """
        Handle incoming audio data from the Omi device.
        
        Args:
            sender: BLE characteristic that sent the data
            data: Raw audio data bytes
        """
        # Only process audio when recording is active
        if self.is_recording:
            decoded_pcm = self.decoder.decode_packet(data)
            if decoded_pcm:
                self.audio_bytes_received += len(decoded_pcm)
                try:
                    self.audio_queue.put_nowait(decoded_pcm)
                except Exception as e:
                    print(f"Queue error: {e}")
    
    async def custom_transcript_handler(self, transcript: str) -> None:
        """
        Custom handler for transcripts during recording.
        
        Args:
            transcript: The transcribed text
        """
        if self.is_recording:
            print(f"🎤 [RECORDING] {transcript}")
        else:
            # This shouldn't happen but handle it gracefully
            print(f"📝 [IDLE] {transcript}")
    
    async def run(self) -> None:
        """Run the recording session."""
        print("=" * 60)
        print("🎮 Omi Button Recording Example")
        print("=" * 60)
        print("Instructions:")
        print("  • Long press button to START recording")
        print("  • Long press again to STOP recording")
        print("  • Audio feedback will confirm state changes")
        print("=" * 60)
        print(f"Connecting to device: {OMI_MAC}")
        print()
        
        # Start both Bluetooth connection and transcription service
        await asyncio.gather(
            listen_to_omi_with_button(
                OMI_MAC,
                AUDIO_CHAR_UUID,
                self.handle_audio_data,
                self.button_handler
            ),
            transcribe(
                self.audio_queue,
                self.api_key,
                on_transcript=self.custom_transcript_handler
            )
        )


async def main() -> None:
    """Main entry point for the example."""
    # Get Deepgram API key from environment
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ Error: DEEPGRAM_API_KEY environment variable not set")
        print("Get your free API key at: https://deepgram.com")
        return
    
    # Create and run recording session
    session = RecordingSession(api_key)
    
    try:
        await session.run()
    except KeyboardInterrupt:
        print("\n\n👋 Recording session terminated by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        # Clean up audio feedback system
        session.audio_feedback.stop()


if __name__ == "__main__":
    asyncio.run(main())