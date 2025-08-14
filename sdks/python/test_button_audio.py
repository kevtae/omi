#!/usr/bin/env python3
"""
Simple test script demonstrating built-in audio feedback in ButtonHandler.

This shows how the ButtonHandler now has built-in "Recording started" and 
"Recording stopped" audio feedback that works automatically.

Usage:
    python test_button_audio.py [MAC_ADDRESS]
"""

import asyncio
import sys
import os
from typing import Any

# Add the current directory to Python path so we can import omi modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from omi.bluetooth import print_devices, listen_to_omi_with_button
from omi.button import ButtonHandler, ButtonState


class SimpleButtonTest:
    """Simple test with built-in audio feedback."""
    
    def __init__(self, mac_address: str):
        self.mac_address = mac_address
        
        # ButtonHandler with haptic feedback
        self.button_handler = ButtonHandler(
            on_button_event=self._on_button_event
        )
    
    def _on_button_event(self, state: ButtonState) -> None:
        """Log button events."""
        state_names = {
            ButtonState.IDLE: "IDLE",
            ButtonState.LONG_PRESS_START: "LONG_PRESS_START",
            ButtonState.LONG_PRESS_RELEASE: "LONG_PRESS_RELEASE"
        }
        print(f"🔘 Button: {state_names.get(state, f'UNKNOWN({state})')}")
        print(f"📊 Recording State: {'RECORDING' if self.button_handler.is_recording() else 'IDLE'}")
        
    def handle_audio_data(self, sender: Any, data: bytes) -> None:
        """Handle audio data (just count packets)."""
        pass  # We don't need to process audio for this test
    
    async def run_test(self, duration: int = 60) -> None:
        """Run the simple audio feedback test."""
        print("=" * 70)
        print("🔊 BUILT-IN AUDIO FEEDBACK TEST")
        print("=" * 70)
        print(f"Device MAC: {self.mac_address}")
        print(f"Test Duration: {duration} seconds")
        print()
        print("Features:")
        print("  ✅ Enhanced haptic feedback patterns")
        print("  ✅ Haptic vibration feedback") 
        print("  ✅ Firmware bug workaround")
        print()
        print("Instructions:")
        print("  • Long press button (1+ seconds) to toggle recording")
        print("  • Feel for haptic vibration patterns")
        print("  • Watch console for button events")
        print("=" * 70)
        print()
        
        audio_char_uuid = "19B10001-E8F2-537E-4F6C-D104768A1214"
        
        try:
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
        finally:
            # Clean up audio feedback resources
            self.button_handler.cleanup()
        
        print("\n" + "=" * 70)
        print("📊 TEST SUMMARY")
        print("=" * 70)
        print(f"Final recording state: {'RECORDING' if self.button_handler.is_recording() else 'IDLE'}")
        print("Enhanced haptic feedback patterns were used during the test.")


async def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        mac_address = sys.argv[1]
    else:
        print("No MAC address provided. Scanning for devices...\n")
        print_devices()
        print("\nUsage: python test_button_audio.py MAC_ADDRESS")
        print("Example: python test_button_audio.py C9DDDACB-CA1E-CDD6-7A17-59A2A5303CDA")
        return
    
    try:
        duration_input = input(f"\nEnter test duration in seconds (default 30): ").strip()
        duration = int(duration_input) if duration_input else 30
    except (ValueError, KeyboardInterrupt):
        duration = 30
    
    test = SimpleButtonTest(mac_address)
    
    try:
        await test.run_test(duration)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        # Test completed
        pass


if __name__ == "__main__":
    asyncio.run(main())