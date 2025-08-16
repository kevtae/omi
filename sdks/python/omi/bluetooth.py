"""
Fixed version of bluetooth.py with working audio pause mechanism
"""

import asyncio
from typing import Any, Callable, Optional
from bleak import BleakClient

from .button import ButtonHandler

# Bluetooth UUIDs
SPEAKER_SERVICE_UUID = "cab1ab95-2ea5-4f4d-bb56-874b72cfc984"
SPEAKER_CHARACTERISTIC_UUID = "cab1ab96-2ea5-4f4d-bb56-874b72cfc984"
BUTTON_SERVICE_UUID = "23BA7924-0000-1000-7450-346EAC492E92"
BUTTON_TRIGGER_CHARACTERISTIC_UUID = "23BA7925-0000-1000-7450-346EAC492E92"

def print_devices() -> None:
    """Scan for and print available Bluetooth devices."""
    import asyncio
    from bleak import BleakScanner
    
    async def scan():
        devices = await BleakScanner.discover()
        for device in devices:
            print(f"{device.address}: {device.name}")
    
    asyncio.run(scan())

async def listen_to_omi(mac_address: str, char_uuid: str, data_handler: Callable[[Any, bytes], None]) -> None:
    """
    Connect to Omi device and listen for data on specified characteristic.
    
    Args:
        mac_address: Bluetooth MAC address of the Omi device
        char_uuid: UUID of the characteristic to listen to
        data_handler: Function to handle incoming data
    """
    async with BleakClient(mac_address) as client:
        print(f"Connected to {mac_address}")
        await client.start_notify(char_uuid, data_handler)
        print("Listening for data...")
        await asyncio.sleep(99999)

async def listen_to_omi_with_button(
    mac_address: str,
    audio_char_uuid: str,
    audio_handler: Callable[[Any, bytes], None],
    button_handler: Optional[ButtonHandler] = None
) -> None:
    """
    Connect to Omi device and listen for both audio data and button events.
    FIXED VERSION with working audio pause mechanism.
    """
    async with BleakClient(mac_address) as client:
        print(f"Connected to {mac_address}")
        
        # Setup haptic feedback functions (same as original)
        async def play_haptic(level: int) -> None:
            try:
                services = client.services
                speaker_service = None
                for service in services:
                    if service.uuid.lower() == SPEAKER_SERVICE_UUID.lower():
                        speaker_service = service
                        break
                
                if speaker_service:
                    speaker_char = None
                    for char in speaker_service.characteristics:
                        if char.uuid.lower() == SPEAKER_CHARACTERISTIC_UUID.lower():
                            speaker_char = char
                            break
                    
                    if speaker_char:
                        await client.write_gatt_char(speaker_char, bytes([level & 0xFF]))
            except Exception:
                pass
        
        async def play_enhanced_haptic(pattern_type: str) -> None:
            try:
                services = client.services
                speaker_service = None
                for service in services:
                    if service.uuid.lower() == SPEAKER_SERVICE_UUID.lower():
                        speaker_service = service
                        break
                
                if speaker_service:
                    speaker_char = None
                    for char in speaker_service.characteristics:
                        if char.uuid.lower() == SPEAKER_CHARACTERISTIC_UUID.lower():
                            speaker_char = char
                            break
                    
                    if speaker_char:
                        if pattern_type == "start":
                            await client.write_gatt_char(speaker_char, bytes([2]))  # 100ms pulse
                        elif pattern_type == "stop":
                            await client.write_gatt_char(speaker_char, bytes([3]))  # 500ms pulse
                        else:
                            await client.write_gatt_char(speaker_char, bytes([1]))  # 20ms pulse
            except Exception:
                pass

        # Start audio notifications FIRST
        await client.start_notify(audio_char_uuid, audio_handler)
        print("Listening for audio data...")
        
        # Setup button handling with audio pause mechanism
        if button_handler:
            # Set up haptic callbacks
            button_handler._enhanced_haptic_callback = lambda pattern: asyncio.create_task(play_enhanced_haptic(pattern))
            button_handler.haptic_callback = lambda level: asyncio.create_task(play_haptic(level))
            
            # Find button service and characteristic
            services = client.services
            button_service = None
            for service in services:
                if service.uuid.lower() == BUTTON_SERVICE_UUID.lower():
                    button_service = service
                    break
            
            if button_service:
                button_char = None
                for char in button_service.characteristics:
                    if char.uuid.lower() == BUTTON_TRIGGER_CHARACTERISTIC_UUID.lower():
                        button_char = char
                        break
                
                if button_char:
                    # Audio pause state tracking
                    audio_paused = False
                    
                    async def pause_audio_for_button():
                        """Pause audio temporarily for button detection"""
                        nonlocal audio_paused
                        if not audio_paused:
                            try:
                                print("🔇 AUDIO PAUSED for button detection")
                                await client.stop_notify(audio_char_uuid)
                                audio_paused = True
                                
                                # Wait for button detection window
                                await asyncio.sleep(1.5)
                                
                                # Resume audio
                                await client.start_notify(audio_char_uuid, audio_handler)
                                audio_paused = False
                                print("🔊 AUDIO RESUMED")
                                
                            except Exception as e:
                                print(f"Error in audio pause: {e}")
                                audio_paused = False
                    
                    def handle_button_data(sender: Any, data: bytes) -> None:
                        """Process button data with audio pause on START events"""
                        # Process the button event normally
                        button_state = button_handler.process_button_data(data)
                        
                        # Check if this is a LONG_PRESS_START (value 3) and pause audio
                        if len(data) > 0 and data[0] == 3:  # LONG_PRESS_START
                            asyncio.create_task(pause_audio_for_button())
                    
                    await client.start_notify(button_char, handle_button_data)
        
        # Keep connection alive
        await asyncio.sleep(99999)