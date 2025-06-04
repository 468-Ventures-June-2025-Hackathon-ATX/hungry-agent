import React, { useState, useEffect, useCallback } from 'react';
// Remove socket.io-client import - we'll use native WebSockets
import axios from 'axios';
import { 
  Mic, 
  MicOff, 
  ShoppingCart, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Users,
  Activity,
  Truck,
  Phone
} from 'lucide-react';
import './index.css';

// Components
import SystemStatus from './components/SystemStatus';
import OrderCard from './components/OrderCard';
import VoiceActivity from './components/VoiceActivity';
import SessionList from './components/SessionList';
import OrderStats from './components/OrderStats';
import VoiceInput from './components/VoiceInput';
import DeliverySettings from './components/DeliverySettings';
import BatchOrderStatus from './components/BatchOrderStatus';

function App() {
  // State management
  const [socket, setSocket] = useState(null);
  const [connected, setConnected] = useState(false);
  const [orders, setOrders] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [systemStatus, setSystemStatus] = useState({
    orchestrator: false,
    uber_mcp: false,
    doordash_mcp: false,
    active_sessions: 0,
    total_orders_today: 0
  });
  const [voiceActivities, setVoiceActivities] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [deliveryAddress, setDeliveryAddress] = useState('');

  // Initialize WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      const ws = new WebSocket('ws://localhost:8000/ws');
      
      ws.onopen = () => {
        console.log('Connected to Hungry Agent server');
        setConnected(true);
        setSocket(ws);
      };
      
      ws.onclose = () => {
        console.log('Disconnected from server');
        setConnected(false);
        setSocket(null);
        
        // Attempt to reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnected(false);
      };
      
      ws.onmessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          handleRealtimeUpdate(update);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };
      
      return ws;
    };
    
    const ws = connectWebSocket();
    
    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, []);

  // Handle real-time updates from WebSocket
  const handleRealtimeUpdate = useCallback((update) => {
    console.log('Real-time update:', update);

    switch (update.type) {
      case 'system_status':
        setSystemStatus(update.data);
        break;
      
      case 'order_update':
        if (update.data.action === 'order_created') {
          // Add new order
          const newOrder = {
            id: update.data.order_id,
            session_id: update.data.session_id,
            platform: update.data.platform,
            status: update.data.status,
            restaurant_name: update.data.restaurant_name,
            items: update.data.items,
            created_at: new Date().toISOString()
          };
          setOrders(prev => [newOrder, ...prev]);
        } else if (update.data.action === 'status_updated') {
          // Update existing order
          setOrders(prev => prev.map(order => 
            order.id === update.data.order_id 
              ? { ...order, status: update.data.status }
              : order
          ));
        }
        break;
      
      case 'voice_activity':
        const activity = {
          id: Date.now(),
          session_id: update.session_id,
          timestamp: new Date(update.timestamp),
          ...update.data
        };
        
        setVoiceActivities(prev => [activity, ...prev.slice(0, 49)]); // Keep last 50
        
        // Flash update animation
        setTimeout(() => {
          const element = document.querySelector(`[data-session="${update.session_id}"]`);
          if (element) {
            element.classList.add('flash-update');
            setTimeout(() => element.classList.remove('flash-update'), 500);
          }
        }, 100);
        break;
      
      default:
        console.log('Unknown update type:', update.type);
    }
  }, []);

  // Fetch initial data
  useEffect(() => {
    const fetchInitialData = async () => {
      try {
        setLoading(true);
        
        // Fetch orders
        const ordersResponse = await axios.get('/api/orders?limit=50');
        setOrders(ordersResponse.data);
        
        // Fetch sessions
        const sessionsResponse = await axios.get('/api/sessions');
        setSessions(sessionsResponse.data);
        
        // Fetch system status
        const statusResponse = await axios.get('/health');
        setSystemStatus(statusResponse.data);
        
      } catch (error) {
        console.error('Error fetching initial data:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchInitialData();
  }, []);

  // Filter orders by selected session
  const filteredOrders = selectedSession 
    ? orders.filter(order => order.session_id === selectedSession)
    : orders;

  // Filter voice activities by selected session
  const filteredActivities = selectedSession
    ? voiceActivities.filter(activity => activity.session_id === selectedSession)
    : voiceActivities;

  // Handle voice input from microphone
  const handleVoiceInput = async (voiceData) => {
    setIsProcessingVoice(true);
    
    try {
      const sessionId = `voice-session-${Date.now()}`;
      
      // Include delivery address in the voice command context
      let enhancedText = voiceData.text;
      if (deliveryAddress) {
        enhancedText = `${voiceData.text} (Delivery address: ${deliveryAddress})`;
      }
      
      const response = await axios.post('/api/voice/process', {
        text: enhancedText,
        confidence: voiceData.confidence,
        session_id: sessionId,
        timestamp: voiceData.timestamp,
        delivery_address: deliveryAddress
      });
      
      console.log('Voice processing response:', response.data);
      
      // Play Claude's response using TTS
      if (response.data.voice_output && response.data.voice_output.text) {
        await playClaudeResponse(response.data.voice_output.text, sessionId);
      }
      
    } catch (error) {
      console.error('Error processing voice input:', error);
    } finally {
      setIsProcessingVoice(false);
    }
  };

  // Play Claude's response using TTS
  const playClaudeResponse = async (text, sessionId) => {
    try {
      const ttsResponse = await axios.post('http://localhost:5002/synthesize', {
        text: text,
        voice: 'en-US-rf1',
        session_id: sessionId
      });
      
      if (ttsResponse.data.audio_url) {
        const audio = new Audio(`http://localhost:5002${ttsResponse.data.audio_url}`);
        audio.play();
      }
    } catch (error) {
      console.error('Error playing TTS audio:', error);
      // Fallback: use browser speech synthesis
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 0.9;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
      }
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-shimmer w-16 h-16 rounded-full mx-auto mb-4"></div>
          <h2 className="text-xl font-semibold text-gray-900">Loading Hungry Agent Dashboard...</h2>
          <p className="text-gray-600 mt-2">Connecting to voice ordering system</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center">
              <div className="flex items-center space-x-3">
                <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                  <ShoppingCart className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">Hungry Agent</h1>
                  <p className="text-sm text-gray-600">Voice-based Taco Ordering Dashboard</p>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-4">
              {/* Connection status */}
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${connected ? 'bg-success-500' : 'bg-danger-500'}`}></div>
                <span className="text-sm text-gray-600">
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {/* Active sessions count */}
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Users className="w-4 h-4" />
                <span>{systemStatus.active_sessions} active sessions</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          
          {/* Left sidebar - System status and sessions */}
          <div className="lg:col-span-1 space-y-6">
            <SystemStatus status={systemStatus} connected={connected} />
            <SessionList 
              sessions={sessions}
              selectedSession={selectedSession}
              onSelectSession={setSelectedSession}
            />
          </div>

          {/* Main content area */}
          <div className="lg:col-span-3 space-y-6">
            
            {/* Delivery Settings */}
            <DeliverySettings onAddressChange={setDeliveryAddress} />
            
            {/* Voice Input */}
            <VoiceInput 
              onVoiceInput={handleVoiceInput}
              isProcessing={isProcessingVoice}
            />
            
            {/* Stats overview */}
            <OrderStats orders={orders} />
            
            {/* Batch Orders Status */}
            <BatchOrderStatus socket={socket} />
            
            {/* Voice activity feed */}
            <VoiceActivity 
              activities={filteredActivities}
              selectedSession={selectedSession}
            />
            
            {/* Orders list */}
            <div className="card">
              <div className="card-header">
                <h2 className="text-lg font-semibold text-gray-900">
                  Recent Orders
                  {selectedSession && (
                    <span className="ml-2 text-sm font-normal text-gray-600">
                      (Session: {selectedSession.slice(0, 8)}...)
                    </span>
                  )}
                </h2>
                <div className="flex items-center space-x-2">
                  <span className="text-sm text-gray-600">
                    {filteredOrders.length} orders
                  </span>
                  {selectedSession && (
                    <button
                      onClick={() => setSelectedSession(null)}
                      className="text-sm text-primary-600 hover:text-primary-700"
                    >
                      Show all
                    </button>
                  )}
                </div>
              </div>
              
              <div className="space-y-4">
                {filteredOrders.length === 0 ? (
                  <div className="text-center py-8">
                    <ShoppingCart className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-gray-900 mb-2">No orders yet</h3>
                    <p className="text-gray-600">
                      {selectedSession 
                        ? 'No orders found for this session'
                        : 'Orders will appear here when customers start ordering tacos'
                      }
                    </p>
                  </div>
                ) : (
                  filteredOrders.map((order) => (
                    <OrderCard 
                      key={order.id} 
                      order={order}
                      onStatusUpdate={(orderId, newStatus) => {
                        // Update order status via API
                        axios.post(`/api/orders/${orderId}/status`, { status: newStatus })
                          .catch(error => console.error('Error updating order status:', error));
                      }}
                    />
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default App;
