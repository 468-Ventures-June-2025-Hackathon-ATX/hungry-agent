import React from 'react';
import { 
  Server, 
  Wifi, 
  WifiOff, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  Activity
} from 'lucide-react';

const SystemStatus = ({ status, connected }) => {
  const services = [
    {
      name: 'Orchestrator',
      key: 'orchestrator',
      description: 'Main coordination service'
    },
    {
      name: 'Uber Eats MCP',
      key: 'uber_eats_mcp',
      description: 'Direct Uber Eats ordering'
    },
    {
      name: 'Batch Ordering',
      key: 'batch_ordering',
      description: 'Multi-restaurant batch orders'
    },
    {
      name: 'STT Service',
      key: 'stt_service',
      description: 'Speech-to-text processing'
    },
    {
      name: 'TTS Service',
      key: 'tts_service',
      description: 'Text-to-speech synthesis'
    }
  ];

  const getStatusIcon = (isOnline) => {
    if (isOnline) {
      return <CheckCircle className="w-4 h-4 text-success-500" />;
    } else {
      return <XCircle className="w-4 h-4 text-danger-500" />;
    }
  };

  const getStatusBadge = (isOnline) => {
    if (isOnline) {
      return <span className="badge badge-success">Online</span>;
    } else {
      return <span className="badge badge-danger">Offline</span>;
    }
  };

  const overallHealth = services.reduce((acc, service) => {
    return acc + (status[service.key] ? 1 : 0);
  }, 0);

  const healthPercentage = Math.round((overallHealth / services.length) * 100);

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <Server className="w-5 h-5 mr-2" />
          System Status
        </h2>
        <div className="flex items-center space-x-2">
          {connected ? (
            <Wifi className="w-4 h-4 text-success-500" />
          ) : (
            <WifiOff className="w-4 h-4 text-danger-500" />
          )}
        </div>
      </div>

      {/* Overall health indicator */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">Overall Health</span>
          <span className="text-sm text-gray-600">{healthPercentage}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div 
            className={`h-2 rounded-full transition-all duration-300 ${
              healthPercentage >= 80 ? 'bg-success-500' :
              healthPercentage >= 60 ? 'bg-warning-500' : 'bg-danger-500'
            }`}
            style={{ width: `${healthPercentage}%` }}
          ></div>
        </div>
      </div>

      {/* Service status list */}
      <div className="space-y-3">
        {services.map((service) => (
          <div 
            key={service.key}
            className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
          >
            <div className="flex items-center space-x-3">
              {getStatusIcon(status[service.key])}
              <div>
                <div className="text-sm font-medium text-gray-900">
                  {service.name}
                </div>
                <div className="text-xs text-gray-600">
                  {service.description}
                </div>
              </div>
            </div>
            {getStatusBadge(status[service.key])}
          </div>
        ))}
      </div>

      {/* Connection status */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <Activity className="w-4 h-4 text-gray-500" />
            <span className="text-sm text-gray-700">WebSocket Connection</span>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${
              connected ? 'bg-success-500 animate-pulse' : 'bg-danger-500'
            }`}></div>
            <span className="text-sm text-gray-600">
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>
      </div>

      {/* System metrics */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-2xl font-bold text-primary-600">
              {status.active_sessions || 0}
            </div>
            <div className="text-xs text-gray-600">Active Sessions</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-warning-600">
              {status.active_batch_orders || 0}
            </div>
            <div className="text-xs text-gray-600">Batch Orders</div>
          </div>
          <div>
            <div className="text-2xl font-bold text-success-600">
              {status.total_orders_today || 0}
            </div>
            <div className="text-xs text-gray-600">Orders Today</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SystemStatus;
