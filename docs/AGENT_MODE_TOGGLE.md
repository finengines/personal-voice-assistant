# Agent Mode Toggle

A beautiful, minimal toggle component that allows users to switch between Fast Mode and Enhanced Mode for the voice agent.

## Features

- **Fast Mode**: Minimal latency response with basic memory functionality
- **Enhanced Mode**: Advanced memory system with contextual understanding
- **Voice Optimization**: Automatically applies voice-specific optimizations when in voice mode
- **Real-time Communication**: Changes are sent to the backend and confirmed
- **Persistent Settings**: Mode preference is saved in localStorage
- **Visual Feedback**: Smooth animations and confirmation indicators

## UI Components

### AgentModeToggle Component

Located: `frontend/src/components/AgentModeToggle.jsx`

**Props:**
- `isEnhancedMode`: boolean - Current mode state
- `onModeChange`: function - Callback when mode changes
- `disabled`: boolean - Disable toggle during connection
- `className`: string - Additional CSS classes

**Features:**
- Sleek sliding toggle with icons
- Hover effects and smooth transitions
- Accessibility support (focus-visible, reduced-motion)
- Responsive design for mobile
- High contrast mode support

### Integration

The toggle is integrated into the `MinimalVoiceAgent` component and appears:
- Between the header and main interaction area
- Disabled when agent is connected (prevents mid-conversation changes)
- Shows current mode in connection status

## Backend Integration

### Memory Performance Modes

The backend `DynamicAgent` supports multiple performance profiles:

**Fast Mode:**
```javascript
{
  timeout: 0.8s,
  min_query_length: 5,
  cache_ttl: 600s,
  aggressive_filtering: true
}
```

**Enhanced Mode (Voice):**
```javascript
{
  timeout: 0.6s,        // Ultra-fast for voice
  min_query_length: 4,
  cache_ttl: 900s,
  voice_optimized: true,
  semantic_search: true
}
```

**Enhanced Mode (Standard):**
```javascript
{
  timeout: 1.0s,
  min_query_length: 3,
  cache_ttl: 300s,
  semantic_search: true,
  contextual_matching: true
}
```

### Communication Protocol

**Frontend → Backend:**
```json
{
  "type": "agent-mode-change",
  "mode": "enhanced|fast",
  "timestamp": "2025-01-23T..."
}
```

**Backend → Frontend:**
```json
{
  "type": "mode-change-confirmed",
  "mode": "enhanced|fast", 
  "voice_optimized": true,
  "search_timeout": 0.6,
  "timestamp": "2025-01-23T..."
}
```

## Performance Impact

### Fast Mode
- **Memory Search**: Disabled for most queries
- **Response Time**: ~200-400ms
- **Memory Usage**: Minimal
- **Best For**: Quick conversations, simple queries

### Enhanced Mode  
- **Memory Search**: Full semantic analysis
- **Response Time**: ~600-1000ms (voice optimized)
- **Memory Usage**: Advanced caching and context
- **Best For**: Complex assistance, work help, contextual conversations

## Technical Implementation

### Frontend Changes

1. **AgentModeToggle Component**: Beautiful toggle with sliding animation
2. **App.jsx**: State management and backend communication
3. **MinimalVoiceAgent**: Integration and status display
4. **MemoryIndicator**: Mode change confirmations

### Backend Changes

1. **DynamicAgent**: Advanced memory system with multiple performance profiles
2. **Configuration Handlers**: Real-time mode switching via LiveKit data streams
3. **Voice Optimizations**: Automatic voice-specific settings
4. **Memory Performance**: Caching, parallel search, semantic analysis

### Key Features

- **Real-time Mode Switching**: Changes apply immediately
- **Voice-Safe Operations**: No blocking operations during voice interactions
- **Persistent Preferences**: Settings saved across sessions
- **Visual Confirmation**: UI feedback for mode changes
- **Performance Monitoring**: Built-in metrics and logging

## Usage Examples

### Basic Usage
```jsx
<AgentModeToggle
  isEnhancedMode={agentMode}
  onModeChange={handleModeChange}
  disabled={isConnected}
/>
```

### With Custom Styling
```jsx
<AgentModeToggle
  isEnhancedMode={agentMode}
  onModeChange={handleModeChange}
  className="compact"
  disabled={isConnected}
/>
```

### Backend Configuration
```python
# Enable voice optimizations
agent.enable_voice_optimizations()

# Manual configuration
agent.configure_memory_performance("voice")  # or "fast", "balanced", "comprehensive"
```

## Design Philosophy

The toggle follows the app's minimal, black-and-white aesthetic:

- **Minimal**: Clean design without unnecessary elements
- **Accessible**: Full keyboard navigation and screen reader support  
- **Responsive**: Works on all screen sizes
- **Performant**: Smooth animations with CSS-only transitions
- **Consistent**: Matches existing UI patterns and spacing

## Future Enhancements

- Additional performance profiles (e.g., "balanced", "power-user")
- Per-conversation mode memory
- Usage analytics and recommendations
- Advanced configuration options
- Integration with user preferences system 