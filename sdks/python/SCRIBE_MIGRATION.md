# OMI to Scribe Integration Migration Plan

## Overview
This document tracks the progress of integrating OMI real-time transcription with the existing Scribe service in the Operaitor chat application.

## Current Status: Planning ✅

## Architecture Analysis Complete ✅

### Current Scribe Service Flow:
1. **Audio Input**: Manual audio file upload or AWS Medical WebSocket
2. **Transcription**: Post-processing via Deepgram or similar
3. **Storage**: `scribe_sessions` table with transcription text
4. **AI Processing**: Worker queue generates medical notes using OpenAI/Claude
5. **Output**: Structured medical notes (SOAP, consultation notes)

### Current OMI Service Flow:
1. **Device Connection**: Bluetooth connection to OMI device via MAC address
2. **Real-time Audio**: Streams audio via characteristic UUID `19B10001-E8F2-537E-4F6C-D104768A1214`
3. **Transcription**: Real-time transcription via Deepgram WebSocket
4. **Storage**: In-memory transcriptions array (temporary)
5. **Timeout**: Currently limited to 30 seconds per session

## Migration Tasks

### Phase 1: Core Integration 🔄
- [ ] **Create OMI WebSocket Endpoint**
  - [ ] Add `/omi/ws/transcription/{session_id}` WebSocket endpoint
  - [ ] Remove 30-second timeout limitation
  - [ ] Stream transcriptions continuously until manually stopped
  - [ ] Handle WebSocket reconnection and error recovery

- [ ] **Integrate with Scribe Sessions**
  - [ ] Create `/omi/sessions/start` endpoint to initialize scribe session with OMI
  - [ ] Store OMI transcriptions in `scribe_sessions.transcription` field
  - [ ] Update session status as transcription progresses
  - [ ] Add `transcription_source` field (values: 'omi', 'audio_file', 'manual')

### Phase 2: Database Schema Updates 📊
- [ ] **Extend scribe_sessions table**
  ```sql
  ALTER TABLE scribe_sessions 
  ADD COLUMN omi_device_mac VARCHAR(255),
  ADD COLUMN transcription_source VARCHAR(20) DEFAULT 'audio_file';
  ```
- [ ] **Create omi_devices table**
  ```sql
  CREATE TABLE omi_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    mac_address VARCHAR(255) NOT NULL,
    device_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'inactive',
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  );
  ```

### Phase 3: Service Layer Integration 🔧
- [ ] **Create OmiScribeService**
  - [ ] Extend/compose with existing ScribeService
  - [ ] Methods: `start_omi_session()`, `stream_transcription()`, `end_session()`
  - [ ] Handle device registration and management
  - [ ] Link OMI sessions to business/provider context

- [ ] **Update Worker Queue**
  - [ ] Modify existing scribe queue processing to handle OMI-sourced sessions
  - [ ] Reuse existing note generation pipeline
  - [ ] Maintain backward compatibility with audio file scribe sessions

### Phase 4: API Endpoints 🌐
- [ ] **Core Session Management**
  - [ ] `POST /omi/sessions/start` - Initialize OMI scribe session
  - [ ] `WS /omi/sessions/{session_id}/stream` - Real-time transcription streaming
  - [ ] `POST /omi/sessions/{session_id}/end` - End session and queue note generation
  - [ ] `GET /omi/sessions/{session_id}/status` - Session and transcription status

- [ ] **Device Management**
  - [ ] `GET /omi/devices` - List registered OMI devices for business
  - [ ] `POST /omi/devices/register` - Register new OMI device to business
  - [ ] `DELETE /omi/devices/{mac_address}` - Remove device registration

- [ ] **Note Generation Integration**
  - [ ] `POST /omi/sessions/{session_id}/generate-note` - Trigger AI note generation
  - [ ] Integrate with existing `/scribe/notes/{request_id}/status` polling

### Phase 5: Frontend Integration 🎨
- [ ] **Scribe UI Updates**
  - [ ] Add OMI device selection/connection interface
  - [ ] Real-time transcription display during recording
  - [ ] Device status indicators (connected, streaming, disconnected)
  - [ ] Session management controls (start, pause, stop)

- [ ] **WebSocket Client**
  - [ ] Implement WebSocket connection for real-time transcription updates
  - [ ] Handle connection drops and reconnection
  - [ ] Display streaming transcription with timestamps

### Phase 6: Testing & Quality Assurance 🧪
- [ ] **Unit Tests**
  - [ ] OMI device connection and transcription
  - [ ] Session management and database operations
  - [ ] Note generation with OMI-sourced transcriptions

- [ ] **Integration Tests**
  - [ ] End-to-end OMI to note generation flow
  - [ ] WebSocket streaming and reconnection
  - [ ] Multiple concurrent OMI sessions

- [ ] **Manual Testing**
  - [ ] Test with actual OMI hardware
  - [ ] Verify audio quality and transcription accuracy
  - [ ] Validate generated medical notes quality

## Technical Considerations

### Dependencies
- ✅ omi-sdk already installed (`pip install -e ".[feedback]"`)
- ✅ deepgram-sdk available for transcription
- ✅ Existing WebSocket infrastructure in place
- ✅ Redis queue system for worker processing

### Integration Points
- ✅ Reuse ScribeService.generate_note() for AI processing
- ✅ Leverage existing worker queue (SCRIBE_QUEUE_NAME)
- ✅ Maintain compatibility with current scribe frontend
- ✅ Use existing authentication and business context

### Performance Considerations
- Real-time transcription requires stable WebSocket connections
- Multiple concurrent OMI sessions per business
- Bluetooth range limitations (typical 10-30 feet)
- Battery life considerations for OMI devices

### Security & Privacy
- HIPAA compliance for medical transcriptions
- Secure WebSocket connections (WSS)
- Business-level access controls for OMI devices
- Audit trail for transcription sessions

## Milestones

- **Milestone 1**: Core WebSocket streaming (Week 1)
- **Milestone 2**: Database integration and session management (Week 2)
- **Milestone 3**: Complete API and service layer (Week 3)
- **Milestone 4**: Frontend integration and testing (Week 4)

## Notes
- Maintain backward compatibility with existing audio-file based scribe functionality
- OMI integration should be additive, not replacing existing features
- Consider graceful degradation when OMI devices are unavailable
- Plan for future multi-device scenarios (multiple OMI devices per session)

---

**Last Updated**: 2025-08-14
**Status**: Planning Complete, Ready for Implementation


## OMI-Scribe Integration Architecture

### Button-Controlled Recording Flow
The OMI device integration follows a seamless, button-controlled workflow:

1. **Background OMI Service**: Continuously listens for registered OMI devices
2. **Button Press Detection**: User long-presses OMI button to start recording
3. **Auto-Session Creation**: System automatically creates scribe session linked to device's business/provider
4. **Real-time Transcription**: Streams transcription to any connected web interfaces
5. **Recording Stop**: Another button press stops recording and triggers note generation
6. **Web Interface**: Passive viewer showing active sessions and real-time transcription

### Database Requirements for OMI Integration
```sql
-- Extend scribe_sessions for OMI integration
ALTER TABLE scribe_sessions 
ADD COLUMN omi_device_mac VARCHAR(255),
ADD COLUMN transcription_source VARCHAR(20) DEFAULT 'audio_file';

-- New table for device-to-business mapping
CREATE TABLE omi_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    provider_id UUID REFERENCES business_users(id),  -- Default provider for device
    mac_address VARCHAR(255) NOT NULL UNIQUE,
    device_name VARCHAR(100),
    status VARCHAR(20) DEFAULT 'inactive',
    last_connected TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### OMI Service Architecture
- **Background Service**: Runs continuously monitoring for button presses
- **Device Registry**: Maps MAC addresses to business/provider context
- **Session Auto-Creation**: Creates scribe sessions when recording starts
- **Real-time Streaming**: WebSocket updates for live transcription
- **Integration**: Uses existing scribe service for note generation
