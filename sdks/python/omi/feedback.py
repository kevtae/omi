"""
Audio feedback system for Omi SDK.

Provides text-to-speech feedback for button events and recording states.
This module is optional and will gracefully degrade if pyttsx3 is not installed.
"""

import asyncio
from typing import Optional, Dict, Any
import threading
import queue


try:
    import pyttsx3
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("Note: pyttsx3 not installed. Audio feedback will be disabled.")
    print("Install with: pip install pyttsx3")


class AudioFeedback:
    """
    Provides audio feedback using text-to-speech.
    
    This class manages TTS operations in a separate thread to avoid
    blocking async operations.
    """
    
    def __init__(self, enabled: bool = True, voice_config: Optional[Dict[str, Any]] = None):
        """
        Initialize the audio feedback system.
        
        Args:
            enabled: Whether to enable audio feedback
            voice_config: Optional configuration for TTS voice settings
        """
        self.enabled = enabled and TTS_AVAILABLE
        self._queue: queue.Queue = queue.Queue()
        self._thread: Optional[threading.Thread] = None
        self._running = False
        
        if self.enabled:
            self._start_tts_thread()
            
            # Configure voice settings if provided
            if voice_config:
                self._configure_voice(voice_config)
    
    def _start_tts_thread(self) -> None:
        """Start the TTS processing thread."""
        if not TTS_AVAILABLE:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._tts_worker, daemon=True)
        self._thread.start()
    
    def _tts_worker(self) -> None:
        """Worker thread for TTS operations."""
        engine = pyttsx3.init()
        
        # Set default voice properties
        engine.setProperty('rate', 175)  # Speed of speech
        engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
        
        while self._running:
            try:
                # Get text from queue with timeout
                text = self._queue.get(timeout=0.1)
                if text is None:  # Shutdown signal
                    break
                    
                engine.say(text)
                engine.runAndWait()
            except queue.Empty:
                continue
            except Exception as e:
                print(f"TTS error: {e}")
    
    def _configure_voice(self, config: Dict[str, Any]) -> None:
        """Configure TTS voice settings."""
        # This would be expanded to actually configure the engine
        pass
    
    def speak(self, text: str) -> None:
        """
        Speak the given text.
        
        Args:
            text: Text to speak
        """
        if self.enabled:
            self._queue.put(text)
    
    async def speak_async(self, text: str) -> None:
        """
        Speak the given text asynchronously.
        
        Args:
            text: Text to speak
        """
        if self.enabled:
            # Run in executor to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.speak, text)
    
    def stop(self) -> None:
        """Stop the TTS system and clean up resources."""
        if self._running:
            self._running = False
            self._queue.put(None)  # Shutdown signal
            if self._thread:
                self._thread.join(timeout=1.0)
    
    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.stop()


class RecordingFeedback:
    """Specialized feedback for recording states."""
    
    def __init__(self, audio_feedback: Optional[AudioFeedback] = None):
        """
        Initialize recording feedback.
        
        Args:
            audio_feedback: Optional AudioFeedback instance to use
        """
        self.audio = audio_feedback or AudioFeedback()
    
    def on_recording_start(self) -> None:
        """Provide feedback when recording starts."""
        self.audio.speak("Recording started")
        print("🎤 Audio feedback: Recording started")
    
    def on_recording_stop(self) -> None:
        """Provide feedback when recording stops."""
        self.audio.speak("Recording stopped")
        print("🔇 Audio feedback: Recording stopped")
    
    async def on_recording_start_async(self) -> None:
        """Async version of recording start feedback."""
        await self.audio.speak_async("Recording started")
        print("🎤 Audio feedback: Recording started")
    
    async def on_recording_stop_async(self) -> None:
        """Async version of recording stop feedback."""
        await self.audio.speak_async("Recording stopped")
        print("🔇 Audio feedback: Recording stopped")