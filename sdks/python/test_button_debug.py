#!/usr/bin/env python3
"""
Standalone button test script for debugging Omi button functionality.

Usage:
    python test_button_debug.py [MAC_ADDRESS]

If no MAC address is provided, it will scan for devices first.
"""

import asyncio
import sys
import os
from typing import Any, Optional

# Add the current directory to Python path so we can import omi modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omi.bluetooth import print_devices, listen_to_omi_with_button
from omi.button import ButtonHandler, ButtonState
from omi.decoder import OmiOpusDecoder


class ButtonTestSession:
    """Test session for button debugging."""
    
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        self.audio_queue = asyncio.Queue()
        self.decoder = OmiOpusDecoder()
        self.button_events = []
        self.audio_packets = 0
        
        # Button handler with detailed logging
        self.button_handler = ButtonHandler(
            on_recording_start=self._on_recording_start,
            on_recording_stop=self._on_recording_stop,
            on_button_event=self._on_button_event
        )
    
    def _on_recording_start(self) -> None:
        print("🎙️ RECORDING STARTED - Button handler triggered")
        
    def _on_recording_stop(self) -> None:
        print("⏹️ RECORDING STOPPED - Button handler triggered")
        
    def _on_button_event(self, state: ButtonState) -> None:
        state_names = {
            ButtonState.IDLE: "IDLE",
            ButtonState.LONG_PRESS_START: "LONG_PRESS_START",
            ButtonState.LONG_PRESS_RELEASE: "LONG_PRESS_RELEASE"
        }
        event_name = state_names.get(state, f"UNKNOWN({state})")
        print(f"🔘 Button Event: {event_name} (value: {state})")
        self.button_events.append((state, asyncio.get_event_loop().time()))
        
    def handle_audio_data(self, sender: Any, data: bytes) -> None:
        """Handle audio data and count packets."""
        self.audio_packets += 1
        if self.audio_packets % 100 == 0:  # Log every 100th packet
            print(f"📊 Audio packets received: {self.audio_packets}")
    
    async def run_test(self, duration: int = 60) -> None:
        """Run the button test for specified duration."""
        print("=" * 70)
        print("🧪 OMI BUTTON DEBUG TEST")
        print("=" * 70)
        print(f"Device MAC: {self.mac_address}")
        print(f"Test Duration: {duration} seconds")
        print()
        print("Instructions:")
        print("  • Watch for button service discovery messages")
        print("  • Press and hold button for 2+ seconds")
        print("  • Release button completely")
        print("  • Look for button events and recording state changes")
        print("=" * 70)
        print()
        
        audio_char_uuid = "19B10001-E8F2-537E-4F6C-D104768A1214"
        
        try:
            # Run test with timeout
            await asyncio.wait_for(
                listen_to_omi_with_button(
                    self.mac_address,
                    audio_char_uuid,
                    self.handle_audio_data,
                    self.button_handler
                ),
                timeout=duration
            )
        except asyncio.TimeoutError:
            print(f"\n⏰ Test completed after {duration} seconds")
        except Exception as e:
            print(f"\n❌ Test error: {e}")
        
        # Print summary
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Audio packets received: {self.audio_packets}")
        print(f"Button events captured: {len(self.button_events)}")
        print(f"Final recording state: {'RECORDING' if self.button_handler.is_recording() else 'IDLE'}")
        
        if self.button_events:
            print("\nButton Events Timeline:")
            start_time = self.button_events[0][1]
            for state, timestamp in self.button_events:
                relative_time = timestamp - start_time
                state_name = {
                    ButtonState.IDLE: "IDLE",
                    ButtonState.LONG_PRESS_START: "LONG_PRESS_START", 
                    ButtonState.LONG_PRESS_RELEASE: "LONG_PRESS_RELEASE"
                }.get(state, f"UNKNOWN({state})")
                print(f"  {relative_time:6.1f}s: {state_name}")
        else:
            print("\n⚠️  No button events were captured!")
            print("   Possible issues:")
            print("   - Button service not found on device")
            print("   - Button characteristic not found")
            print("   - Button not pressed long enough (need 1+ seconds)")
            print("   - Bluetooth connection issues")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        mac_address = sys.argv[1]
    else:
        print("No MAC address provided. Scanning for devices...\n")
        print_devices()
        print("\nUsage: python test_button_debug.py MAC_ADDRESS")
        print("Example: python test_button_debug.py C9DDDACB-CA1E-CDD6-7A17-59A2A5303CDA")
        return
    
    # Ask for test duration
    try:
        duration_input = input(f"\nEnter test duration in seconds (default 60): ").strip()
        duration = int(duration_input) if duration_input else 60
    except (ValueError, KeyboardInterrupt):
        duration = 60
    
    test_session = ButtonTestSession(mac_address)
    
    try:
        await test_session.run_test(duration)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())