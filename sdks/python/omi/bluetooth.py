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
                        await client.write_gatt_char(speaker_char, bytes([level & 0xFF]))
            except Exception as e:
                pass
        
        # Enhanced haptic feedback function with start/stop patterns
        async def play_enhanced_haptic(pattern_type: str) -> None:
            """
            Play enhanced haptic patterns for recording start/stop feedback.
            
            Args:
                pattern_type: "start" for recording start, "stop" for recording stop
            """
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
                        if pattern_type == "start":
                            # Recording START: Quick double pulse (energetic, "go!")
                            await client.write_gatt_char(speaker_char, bytes([1]))  # 20ms pulse
                            await asyncio.sleep(0.1)
                            await client.write_gatt_char(speaker_char, bytes([2]))  # 50ms pulse
                        elif pattern_type == "stop":
                            # Recording STOP: Single long pulse (definitive, "done!")
                            await client.write_gatt_char(speaker_char, bytes([3]))  # 500ms pulse
                        else:
                            # Unknown pattern, use basic haptic
                            await client.write_gatt_char(speaker_char, bytes([1]))  # 20ms pulse
            except Exception as e:
                pass

        # Start button notifications if handler provided
        if button_handler:
            # Set up enhanced haptic callback for start/stop patterns
            button_handler._enhanced_haptic_callback = lambda pattern: asyncio.create_task(play_enhanced_haptic(pattern))
            # Keep basic haptic callback for fallback situations
            button_handler.haptic_callback = lambda level: asyncio.create_task(play_haptic(level))
            # Check if button service is available
            services = client.services
            service_list = list(services)
            # Service discovery for button functionality
                
            button_service = None
            for service in service_list:
                if service.uuid.lower() == BUTTON_SERVICE_UUID.lower():
                    button_service = service
                    break
            
            if button_service:
                # Find button characteristic
                button_char = None
                for char in button_service.characteristics:
                    if char.uuid.lower() == BUTTON_TRIGGER_CHARACTERISTIC_UUID.lower():
                        button_char = char
                        break
                
                if button_char:
                    
                    def handle_button_data(sender: Any, data: bytes) -> None:
                        button_handler.process_button_data(data)
                    
                    await client.start_notify(BUTTON_TRIGGER_CHARACTERISTIC_UUID, handle_button_data)
        
        # Keep connection alive
        await asyncio.sleep(99999)
