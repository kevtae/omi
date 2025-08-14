import asyncio
from typing import Callable, Any, Optional
from bleak import BleakScanner, BleakClient
from .button import (
    BUTTON_SERVICE_UUID, 
    BUTTON_TRIGGER_CHARACTERISTIC_UUID, 
    SPEAKER_SERVICE_UUID,
    SPEAKER_CHARACTERISTIC_UUID,
    ButtonHandler
)

def print_devices() -> None:
    """Scan for and print all nearby Bluetooth devices."""
    devices = asyncio.run(BleakScanner.discover())
    for i, d in enumerate(devices):
        print(f"{i}. {d.name} [{d.address}]")

async def listen_to_omi(
    mac_address: str, 
    char_uuid: str, 
    data_handler: Callable[[Any, bytes], None]
) -> None:
    """
    Connect to Omi device and listen for audio data.
    
    Args:
        mac_address: Bluetooth MAC address of the Omi device
        char_uuid: UUID of the audio characteristic
        data_handler: Callback function to handle incoming audio data
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
    
    Args:
        mac_address: Bluetooth MAC address of the Omi device
        audio_char_uuid: UUID of the audio characteristic
        audio_handler: Callback function to handle incoming audio data
        button_handler: Optional ButtonHandler instance for button events
    """
    async with BleakClient(mac_address) as client:
        print(f"Connected to {mac_address}")
        
        # Start audio notifications
        await client.start_notify(audio_char_uuid, audio_handler)
        print("Listening for audio data...")
        
        # Setup haptic feedback function
        async def play_haptic(level: int) -> None:
            """Send haptic feedback to the device."""
            try:
                services = client.services
                service_list = list(services)
                
                # Find speaker service
                speaker_service = None
                for service in service_list:
                    if service.uuid.lower() == SPEAKER_SERVICE_UUID.lower():
                        speaker_service = service
                        break
                
                if speaker_service:
                    # Find speaker characteristic
                    speaker_char = None
                    for char in speaker_service.characteristics:
                        if char.uuid.lower() == SPEAKER_CHARACTERISTIC_UUID.lower():
                            speaker_char = char
                            break
                    
                    if speaker_char:
                        print(f"🔊 Playing haptic feedback (level {level})")
                        await client.write_gatt_char(speaker_char, bytes([level & 0xFF]))
                    else:
                        print("⚠️  Speaker characteristic not found for haptic")
                else:
                    print("⚠️  Speaker service not found for haptic")
            except Exception as e:
                print(f"❌ Haptic feedback error: {e}")
        
        # Start button notifications if handler provided
        if button_handler:
            # Set up haptic callback in button handler
            button_handler.haptic_callback = lambda level: asyncio.create_task(play_haptic(level))
            # Check if button service is available
            services = client.services
            service_list = list(services)
            print(f"Found {len(service_list)} services on device:")
            for service in service_list:
                print(f"  Service: {service.uuid}")
                
            button_service = None
            for service in service_list:
                if service.uuid.lower() == BUTTON_SERVICE_UUID.lower():
                    button_service = service
                    break
            
            if button_service:
                print(f"✅ Found button service: {button_service.uuid}")
                # Find button characteristic
                button_char = None
                print(f"Button service has {len(button_service.characteristics)} characteristics:")
                for char in button_service.characteristics:
                    print(f"  Characteristic: {char.uuid} (properties: {char.properties})")
                    if char.uuid.lower() == BUTTON_TRIGGER_CHARACTERISTIC_UUID.lower():
                        button_char = char
                        break
                
                if button_char:
                    print(f"✅ Found button characteristic: {button_char.uuid}")
                    print(f"   Properties: {button_char.properties}")
                    
                    # Create button data handler with debugging
                    import time
                    last_notification_time = None
                    
                    def handle_button_data(sender: Any, data: bytes) -> None:
                        nonlocal last_notification_time
                        current_time = time.time()
                        
                        if last_notification_time is not None:
                            time_diff = current_time - last_notification_time
                            print(f"🔘 Raw button data received: {data.hex()} (length: {len(data)}) [+{time_diff:.2f}s since last]")
                        else:
                            print(f"🔘 Raw button data received: {data.hex()} (length: {len(data)}) [first notification]")
                        
                        last_notification_time = current_time
                        button_handler.process_button_data(data)
                    
                    await client.start_notify(BUTTON_TRIGGER_CHARACTERISTIC_UUID, handle_button_data)
                    print("✅ Listening for button events...")
                else:
                    print("❌ Button characteristic not found on device")
                    print(f"   Expected UUID: {BUTTON_TRIGGER_CHARACTERISTIC_UUID}")
            else:
                print("❌ Button service not found on device")
                print(f"   Expected UUID: {BUTTON_SERVICE_UUID}")
                print("   Available services:")
                for service in services:
                    print(f"     {service.uuid}")
        
        # Keep connection alive
        await asyncio.sleep(99999)
