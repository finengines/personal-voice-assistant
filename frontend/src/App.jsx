import { useState, useEffect, useRef } from 'react';
// import gsap from 'gsap';
import AgentPresets from './AgentPresets';
import MCPManagement from './MCPManagement';
import APIKeyManagement from './APIKeyManagement';
import GlobalSettings from './components/GlobalSettings';
import './App.css';
import MinimalVoiceAgent from './components/MinimalVoiceAgent';
import SettingsModal from './components/SettingsModal';
import { FiMic, FiServer, FiSliders, FiKey, FiSettings, FiLogOut, FiUser } from 'react-icons/fi';
import { AuthProvider } from './components/AuthContext';
import AuthGateway from './components/AuthGateway';
import { useAuth } from './components/AuthContext';

// Main app component (authenticated content)
function MainApp() {
  const { user, logout } = useAuth();
  const [currentView, setCurrentView] = useState('voice');
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [connectionStep, setConnectionStep] = useState('');
  const [isMuted, setIsMuted] = useState(false);
  const [memoryIndicator, setMemoryIndicator] = useState({isVisible:false,type:'',message:''});
  const [toolIndicator, setToolIndicator] = useState({isVisible:false,label:''});
  const [memoryFallback, setMemoryFallback] = useState(false);
  const [status, setStatus] = useState({ message: 'Disconnected', type: 'disconnected' });
  const [livekitUrl, setLivekitUrl] = useState('ws://localhost:7883');
  const [livekitToken, setLivekitToken] = useState('');
  const [debugLog, setDebugLog] = useState([]);
  const [agentReady, setAgentReady] = useState(false);
  const [audioPlaying, setAudioPlaying] = useState(false);
  const [presets, setPresets] = useState([]);
  const [selectedPreset, setSelectedPreset] = useState(null);
  
  const roomRef = useRef(null);
  const appRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const connectionTimeoutRef = useRef(null);
  const [showSettings, setShowSettings] = useState(false);

  // Visual settings
  const [visualSettings, setVisualSettings] = useState({
    visualStyle: 'particles', // 'circle' | 'particles'
    particleDensity: 'medium', // 'low' | 'medium' | 'high'
    particleColor: '#3a3a3a',
  });

  // Audio analyser for particle sphere
  const audioCtxRef = useRef(null);
  const analyserRef = useRef(null);
  const analyserSourceRef = useRef(null);

  // Connection state tracking
  const [connectionState, setConnectionState] = useState({
    tokenGenerated: false,
    roomConnected: false,
    agentJoined: false,
    microphoneEnabled: false,
    readyForSpeech: false
  });

  // Remove useEffect for gsap

  const log = (message) => {
    const timestamp = new Date().toLocaleTimeString();
    const logEntry = `[${timestamp}] ${message}`;
    setDebugLog(prev => [...prev.slice(-50), logEntry]); // Keep last 50 logs
    console.log(logEntry);
  };

  const updateStatus = (message, type) => {
    setStatus({ message, type });
    log(`Status: ${message}`);
  };

  const updateConnectionStep = (step) => {
    setConnectionStep(step);
    log(`Connection step: ${step}`);
  };

  // Check if mediaDevices API is available
  const checkMediaDevices = () => {
    if (!navigator.mediaDevices) {
      console.warn('MediaDevices API not available');
      updateStatus('MediaDevices API not available. Try HTTPS or localhost.', 'error');
      return false;
    }
    return true;
  };

  // Reset connection state completely
  const resetConnectionState = () => {
    setConnectionState({
      tokenGenerated: false,
      roomConnected: false,
      agentJoined: false,
      microphoneEnabled: false,
      readyForSpeech: false
    });
    setAgentReady(false);
    setAudioPlaying(false);
    setIsConnecting(false);
    setConnectionStep('');
    
    // Clear any pending timeouts
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (connectionTimeoutRef.current) {
      clearTimeout(connectionTimeoutRef.current);
      connectionTimeoutRef.current = null;
    }
  };

  const loadPresets = async () => {
    try {
      const { default: config } = await import('./config.js');
      const API_BASE = config.API_BASE_PRESET;
      const response = await fetch(`${API_BASE}/presets`);
      const result = await response.json();
      if (result.success && Array.isArray(result.data)) {
        setPresets(result.data);
        const defaultPreset = result.data.find(p => p.is_default) || result.data[0];
        if (defaultPreset) {
          setSelectedPreset(defaultPreset);
        }
      } else {
        console.error('Invalid presets data:', result);
        setPresets([]);
      }
    } catch (error) {
      console.error('Failed to load presets:', error);
    }
  };

  const handlePresetChange = (preset) => {
    console.log('🔧 PRESET CHANGE DEBUG:', { newPreset: preset, currentSelected: selectedPreset });
    setSelectedPreset(preset);
    // If already connected, disconnect first then reconnect with new preset
    if (isConnected) {
      disconnect();
      // Capture the preset ID to avoid closure issues
      const presetId = preset?.id;
      setTimeout(() => {
        console.log('🔧 RECONNECTING WITH PRESET ID:', presetId);
        connect(presetId);
      }, 500);
    }
  };

  // Generate LiveKit token
  const generateToken = async (presetId) => {
    try {
      console.log('🔧 GENERATE TOKEN DEBUG:', { presetId, selectedPreset });
      updateConnectionStep('Generating token...');
      updateStatus('Generating token...', 'connecting');

      // Import config dynamically to ensure it's loaded
      const { default: config } = await import('./config.js');
      let requestUrl = config.TOKEN_SERVER_URL;
      if (presetId) {
        requestUrl += `?preset_id=${presetId}`;
      }

      console.log('🔧 TOKEN REQUEST URL:', requestUrl);
      log(`Requesting token from: ${requestUrl}`);

      const response = await fetch(requestUrl);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const tokenData = await response.json();

      // update state for debugging / future reconnects but rely on local vars to avoid race
      setLivekitToken(tokenData.token);
      if (tokenData.livekit_url) {
        setLivekitUrl(tokenData.livekit_url.replace('http', 'ws'));
      }

      setConnectionState(prev => ({ ...prev, tokenGenerated: true }));
      updateStatus(`Token ready for room: ${tokenData.room}`, 'disconnected');
      log(`Token generated: ${tokenData.room}`);

      return { token: tokenData.token, url: tokenData.livekit_url.replace('http', 'ws') };
    } catch (error) {
      console.error('Error generating token:', error);
      updateStatus('Failed to generate token. Make sure token server is running.', 'error');
      return {};
    }
  };

  // Load LiveKit client library
  const loadLiveKitClient = () => {
    return new Promise((resolve, reject) => {
      if (window.LivekitClient) {
        resolve(window.LivekitClient);
        return;
      }
      
      log('Loading LiveKit client library...');
      updateConnectionStep('Loading LiveKit client...');
      const script = document.createElement('script');
      script.src = 'https://cdn.jsdelivr.net/npm/livekit-client/dist/livekit-client.umd.min.js';
      script.onload = () => {
        log('LiveKit client library loaded');
        resolve(window.LivekitClient);
      };
      script.onerror = () => {
        log('Failed to load LiveKit client library');
        reject(new Error('Failed to load LiveKit client library'));
      };
      document.head.appendChild(script);
    });
  };

  // Enhanced cleanup function
  const cleanupConnection = () => {
    if (roomRef.current) {
      try {
        // Remove all event listeners to prevent memory leaks
        roomRef.current.removeAllListeners();
        // Disconnect the room
        roomRef.current.disconnect();
        roomRef.current = null;
        log('Room connection cleaned up');
      } catch (error) {
        log(`Error during cleanup: ${error.message}`);
      }
    }
    // Cleanup analyser
    try {
      if (analyserSourceRef.current) {
        analyserSourceRef.current.disconnect();
        analyserSourceRef.current = null;
      }
      if (analyserRef.current) {
        analyserRef.current.disconnect();
        analyserRef.current = null;
      }
      if (audioCtxRef.current && audioCtxRef.current.state !== 'closed') {
        // Keep context for reuse but suspend to save CPU
        audioCtxRef.current.suspend().catch(() => {});
      }
    } catch (e) {
      console.warn('Analyser cleanup error', e);
    }
    
    resetConnectionState();
    setIsConnected(false);
    setIsMuted(false);
  };

  // Connect to LiveKit with enhanced error handling and state management
  const connect = async (presetId) => {
    const { token, url } = await generateToken(presetId);

    let lkUrl = url || livekitUrl;
    // Use the URL as provided by the backend - no need to modify it
    // The backend will provide the correct LiveKit URL for the environment

    const lkToken = token || livekitToken;

    if (!lkUrl || !lkToken) {
      updateStatus('LiveKit URL or token missing', 'error');
      return;
    }
    
    if (!checkMediaDevices()) {
      return;
    }

    // Prevent multiple connection attempts
    if (isConnecting) {
      log('Connection already in progress, ignoring request');
      return;
    }
    
    setIsConnecting(true);
    resetConnectionState();
    
    // Set connection timeout
    connectionTimeoutRef.current = setTimeout(() => {
      if (isConnecting && !isConnected) {
        log('Connection timeout - cleaning up');
        cleanupConnection();
        updateStatus('Connection timeout. Please try again.', 'error');
      }
    }, 30000); // 30 second timeout
    
    try {
      updateConnectionStep('Preparing connection...');
      updateStatus('Connecting...', 'connecting');
      log('Starting connection process...');
      
      const LivekitClient = await loadLiveKitClient();
      const { Room, RoomEvent } = LivekitClient;
      
      updateConnectionStep('Creating room...');
      const room = new Room({
        adaptiveStream: true,
        dynacast: true,
        // Add connection recovery options
        reconnectPolicy: {
          nextRetryDelayInMs: (context) => {
            return Math.min(1000 * Math.pow(2, context.retryCount), 10000);
          },
        },
        disconnectOnPageLeave: true,
      });
      
      roomRef.current = room;
      
      // Enhanced event listeners with better state tracking
      room.on(RoomEvent.Connected, async () => {
        log('Connected to LiveKit room');
        setConnectionState(prev => ({ ...prev, roomConnected: true }));
        updateConnectionStep('Room connected, enabling microphone...');
        updateStatus('Connected - Setting up microphone...', 'connecting');
        
        try {
          log('Enabling microphone...');
          await room.localParticipant.setMicrophoneEnabled(true);
          setConnectionState(prev => ({ ...prev, microphoneEnabled: true }));
          log('Microphone enabled and streaming');
          updateConnectionStep('Waiting for agent...');
          
          // Clear connection timeout since we're connected
          if (connectionTimeoutRef.current) {
            clearTimeout(connectionTimeoutRef.current);
            connectionTimeoutRef.current = null;
          }
          
        } catch (micError) {
          log(`Failed to enable microphone: ${micError.message}`);
          updateStatus('Microphone access failed', 'error');
        }
      });
      
      room.on(RoomEvent.Disconnected, (reason) => {
        log(`Disconnected from room: ${reason}`);
        updateStatus('Disconnected from voice assistant', 'disconnected');
        cleanupConnection();
        
        // Don't auto-reconnect on intentional disconnection
        if (reason !== 'user-initiated' && isConnected) {
          log('Unexpected disconnection, will attempt reconnect...');
          reconnectTimeoutRef.current = setTimeout(() => {
            if (!isConnected && !isConnecting) {
              log('Attempting automatic reconnection...');
              connect(); // This will now call connect without an argument, which will use the default selectedPreset
            }
          }, 3000);
        }
      });
      
      room.on(RoomEvent.ParticipantConnected, (participant) => {
        log(`Participant connected: ${participant.identity}`);
        if (participant.identity.includes('agent')) {
          setConnectionState(prev => ({ ...prev, agentJoined: true }));
          setAgentReady(true);
          updateConnectionStep('Agent joined, ready for speech...');
          updateStatus('Connected and ready', 'connected');
          setIsConnected(true);
          setIsConnecting(false);
          log('Voice assistant ready');
        }
      });
      
      room.on(RoomEvent.ParticipantDisconnected, (participant) => {
        log(`Participant disconnected: ${participant.identity}`);
        if (participant.identity.includes('agent')) {
          setAgentReady(false);
          updateStatus('Agent disconnected', 'error');
        }
      });
      
      room.on(RoomEvent.AudioPlaybackStarted, () => {
        log('Audio playback started');
        setAudioPlaying(true);
      });
      
      room.on(RoomEvent.AudioPlaybackEnded, () => {
        log('Audio playback ended');
        setAudioPlaying(false);
      });
      
      // Handle incoming audio tracks for agent speech
      room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
        try {
          if (track.kind === 'audio' && participant.identity.includes('agent')) {
            const audioElement = track.attach();
            // Play agent audio
            audioElement.play().catch(e => console.error('Audio playback error:', e));
            setAudioPlaying(true);
            // Reset audioPlaying when playback ends
            audioElement.onended = () => setAudioPlaying(false);

            // Set up analyser for particle sphere (tap remote track)
            try {
              const ctx = audioCtxRef.current || new (window.AudioContext || window.webkitAudioContext)();
              audioCtxRef.current = ctx;
              if (ctx.state === 'suspended') ctx.resume().catch(() => {});

              const stream = new MediaStream([track.mediaStreamTrack]);
              const source = ctx.createMediaStreamSource(stream);
              const analyser = ctx.createAnalyser();
              analyser.fftSize = 1024;
              analyser.smoothingTimeConstant = 0.85;
              source.connect(analyser);
              // Do not connect to destination to avoid duplicating audio
              analyserRef.current = analyser;
              analyserSourceRef.current = source;
            } catch (tapErr) {
              console.warn('Failed to create analyser for remote audio:', tapErr);
            }
          }
        } catch (e) {
          console.error('Error handling TrackSubscribed:', e);
        }
      });
      room.on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
        if (track.kind === 'audio' && participant.identity.includes('agent')) {
          setAudioPlaying(false);
          // Release analyser resources on unsubscribe
          if (analyserSourceRef.current) {
            try { analyserSourceRef.current.disconnect(); } catch {}
            analyserSourceRef.current = null;
          }
          if (analyserRef.current) {
            try { analyserRef.current.disconnect(); } catch {}
            analyserRef.current = null;
          }
        }
      });
      
      // Listen for data packets (memory events)
      room.on(RoomEvent.DataReceived, ({ payload, participant, kind }) => {
        // Debug: Log all incoming data packets
        console.log('🔍 DataReceived event:', { 
          payloadSize: payload.byteLength, 
          participant: participant?.identity || 'unknown',
          kind,
          timestamp: new Date().toISOString()
        });
        
        try {
          const text = new TextDecoder().decode(payload);
          console.log('📦 Raw data payload:', text);
          
          const data = JSON.parse(text);
          console.log('📝 Parsed data:', data);
          
          if (data && data.type && data.type.startsWith('memory-')) {
            console.log('🧠 Memory event detected:', data);
            setMemoryIndicator({ isVisible: true, type: data.type, message: data.message || '' });
            // auto hide after 3s
            setTimeout(() => setMemoryIndicator(prev => ({ ...prev, isVisible: false })), 3000);
          }
          if (data && data.type && data.type.startsWith('tool-')) {
            console.log('🔧 Tool event detected:', data);
            const label = data.tool || data.name || data.message || 'Tool used';
            setToolIndicator({ isVisible: true, label });
            setTimeout(() => setToolIndicator(prev => ({ ...prev, isVisible: false })), 2000);
          }
          if (data && data.type === 'memory-fallback') {
            console.log('💭 Memory fallback event detected:', data);
            setMemoryFallback(true);
          }
        } catch (e) {
          console.error('❌ Error parsing data packet:', e, 'Raw payload:', new TextDecoder().decode(payload));
        }
      });
      
      room.on(RoomEvent.LocalTrackPublished, (publication, participant) => {
        log(`Local track published: ${publication.kind}`);
      });
      
      room.on(RoomEvent.LocalTrackUnpublished, (publication, participant) => {
        log(`Local track unpublished: ${publication.kind}`);
      });

      // Add connection error handling
      room.on(RoomEvent.ConnectionStateChanged, (state) => {
        log(`Connection state changed: ${state}`);
        if (state === 'disconnected') {
          updateStatus('Connection lost', 'error');
        }
      });
      
      room.on(RoomEvent.Reconnecting, () => {
        log('Reconnecting to room...');
        updateStatus('Reconnecting...', 'connecting');
      });
      
      room.on(RoomEvent.Reconnected, () => {
        log('Reconnected to room');
        updateStatus('Reconnected', 'connected');
      });
      
      updateConnectionStep('Connecting to room...');
      log('Connecting to LiveKit room...');
      await room.connect(lkUrl, lkToken);
      log('Room connection initiated');
      
    } catch (error) {
      console.error('Error connecting:', error);
      updateStatus('Connection failed: ' + error.message, 'error');
      log(`Connection error: ${error.message}`);
      cleanupConnection();
      setIsConnecting(false);
    }
  };

  // Enhanced disconnect function
  const disconnect = () => {
    log('User initiated disconnect');
    cleanupConnection();
    updateStatus('Disconnected', 'disconnected');
  };

  // Toggle mute
  const toggleMute = () => {
    if (!isConnected || !roomRef.current) return;
    
    const newMutedState = !isMuted;
    setIsMuted(newMutedState);
    
    roomRef.current.localParticipant.setMicrophoneEnabled(!newMutedState);
    log(newMutedState ? 'Microphone muted' : 'Microphone unmuted');
  };

  // Auto-generate token on mount
  useEffect(() => {
    if (!checkMediaDevices()) {
      updateStatus('Please use HTTPS or localhost for microphone access', 'error');
    }
    // Don't auto-generate token - only when user connects
    loadPresets();
    log('Voice Assistant initialized');
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanupConnection();
    };
  }, []);

  // Debug: Track memory indicator state changes
  useEffect(() => {
    console.log('🧠 Memory indicator state changed:', memoryIndicator);
  }, [memoryIndicator]);

  // Debug: Track tool indicator state changes
  useEffect(() => {
    console.log('🔧 Tool indicator state changed:', toolIndicator);
  }, [toolIndicator]);

  // Debug: Track memory fallback state changes
  useEffect(() => {
    console.log('💭 Memory fallback state changed:', memoryFallback);
  }, [memoryFallback]);

  const BottomNav = () => (
    <nav className="bottom-nav">
      <button className={`nav-icon ${currentView==='voice'? 'active': ''}`} onClick={()=>setCurrentView('voice')}><FiMic size={20}/><span>Voice</span></button>
      <button className={`nav-icon ${currentView==='mcp'? 'active': ''}`} onClick={()=>setCurrentView('mcp')}><FiServer size={20}/><span>MCP</span></button>
      <button className={`nav-icon ${currentView==='presets'? 'active': ''}`} onClick={()=>setCurrentView('presets')}><FiSliders size={20}/><span>Presets</span></button>
      <button className={`nav-icon ${currentView==='apikeys'? 'active': ''}`} onClick={()=>setCurrentView('apikeys')}><FiKey size={20}/><span>API Keys</span></button>
      <button className={`nav-icon ${currentView==='globalsettings'? 'active': ''}`} onClick={()=>setCurrentView('globalsettings')}><FiSettings size={20}/><span>Global</span></button>
      <button className="nav-icon auth-nav" onClick={logout} title={`Logout ${user?.email || 'User'}`}>
        <FiLogOut size={20}/>
        <span>Logout</span>
      </button>
    </nav>
  );

  // Enhanced voice props with loading states
  const voiceProps = {
    isConnected,
    isConnecting,
    connectionStep,
    isMuted,
    onConnect: connect,
    onDisconnect: disconnect,
    onToggleMute: toggleMute,
    status,
    debugLog,
    livekitUrl,
    setLivekitUrl,
    livekitToken,
    setLivekitToken,
    memoryIndicator,
    toolIndicator,
    memoryFallback,
    connectionState,
    agentReady,
    audioPlaying,
    presets,
    selectedPreset,
    onPresetChange: handlePresetChange,
  };

  return (
    <div className="container-main" style={{minHeight:'100vh',background:'var(--backgroundColor)'}}>
      {currentView==='voice' && <MinimalVoiceAgent
          {...voiceProps}
          onOpenSettings={() => setShowSettings(true)}
          visualSettings={visualSettings}
          audioAnalyser={analyserRef.current}
        />}
      {currentView!=='voice' && <>{currentView==='mcp' && <MCPManagement/>}{currentView==='presets' && <AgentPresets/>}{currentView==='apikeys' && <APIKeyManagement/>}{currentView==='globalsettings' && <GlobalSettings/>}</>}
      <BottomNav />
      <SettingsModal
        show={showSettings}
        onClose={() => setShowSettings(false)}
        livekitUrl={livekitUrl}
        setLivekitUrl={setLivekitUrl}
        livekitToken={livekitToken}
        setLivekitToken={setLivekitToken}
        onGenerateToken={() => generateToken(selectedPreset?.id)}
        visualSettings={visualSettings}
        setVisualSettings={setVisualSettings}
      />
    </div>
  );
}

// App wrapper with authentication
function App() {
  return (
    <AuthProvider>
      <AuthGateway>
        <MainApp />
      </AuthGateway>
    </AuthProvider>
  );
}

export default App;
// Force build with authentication - Tue Jul 29 22:25:25 BST 2025
