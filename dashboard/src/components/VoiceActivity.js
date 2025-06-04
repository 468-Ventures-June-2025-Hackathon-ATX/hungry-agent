import React from 'react';
import { 
  Mic, 
  MessageSquare, 
  Bot, 
  User,
  Volume2,
  Activity
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const VoiceActivity = ({ activities, selectedSession }) => {
  const getActivityIcon = (action) => {
    switch (action) {
      case 'voice_input':
        return <Mic className="w-4 h-4 text-primary-600" />;
      case 'claude_response':
        return <Bot className="w-4 h-4 text-success-600" />;
      case 'tts_output':
        return <Volume2 className="w-4 h-4 text-warning-600" />;
      default:
        return <Activity className="w-4 h-4 text-gray-600" />;
    }
  };

  const getActivityColor = (action) => {
    switch (action) {
      case 'voice_input':
        return 'border-l-primary-500 bg-primary-50';
      case 'claude_response':
        return 'border-l-success-500 bg-success-50';
      case 'tts_output':
        return 'border-l-warning-500 bg-warning-50';
      default:
        return 'border-l-gray-500 bg-gray-50';
    }
  };

  const VoiceWaveform = ({ isActive = false }) => (
    <div className={`voice-waveform ${isActive ? '' : 'opacity-50'}`}>
      <div className="voice-bar"></div>
      <div className="voice-bar"></div>
      <div className="voice-bar"></div>
      <div className="voice-bar"></div>
      <div className="voice-bar"></div>
    </div>
  );

  const ActivityItem = ({ activity }) => {
    const isVoiceInput = activity.action === 'voice_input';
    const isClaudeResponse = activity.action === 'claude_response';
    
    return (
      <div 
        className={`border-l-4 p-4 rounded-r-lg ${getActivityColor(activity.action)} animate-fade-in`}
        data-session={activity.session_id}
      >
        <div className="flex items-start space-x-3">
          <div className="flex-shrink-0 mt-0.5">
            {getActivityIcon(activity.action)}
          </div>
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center space-x-2">
                <span className="text-sm font-medium text-gray-900">
                  {isVoiceInput ? 'Voice Input' : 
                   isClaudeResponse ? 'AI Response' : 
                   activity.action.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}
                </span>
                {isVoiceInput && activity.confidence && (
                  <span className="text-xs text-gray-500">
                    ({Math.round(activity.confidence * 100)}% confidence)
                  </span>
                )}
              </div>
              
              <div className="flex items-center space-x-2 text-xs text-gray-500">
                <span>
                  Session: {activity.session_id?.slice(0, 8)}...
                </span>
                <span>
                  {formatDistanceToNow(activity.timestamp, { addSuffix: true })}
                </span>
              </div>
            </div>
            
            {/* Voice input text */}
            {isVoiceInput && activity.text && (
              <div className="mb-2">
                <div className="flex items-center space-x-2 mb-1">
                  <User className="w-3 h-3 text-gray-500" />
                  <span className="text-xs text-gray-600">User said:</span>
                </div>
                <p className="text-sm text-gray-900 bg-white p-2 rounded border">
                  "{activity.text}"
                </p>
              </div>
            )}
            
            {/* Claude response */}
            {isClaudeResponse && (
              <div className="space-y-2">
                {activity.response && (
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <Bot className="w-3 h-3 text-gray-500" />
                      <span className="text-xs text-gray-600">AI responded:</span>
                    </div>
                    <p className="text-sm text-gray-900 bg-white p-2 rounded border">
                      {activity.response}
                    </p>
                  </div>
                )}
                
                {/* Function calls */}
                {activity.function_calls && activity.function_calls.length > 0 && (
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <Activity className="w-3 h-3 text-gray-500" />
                      <span className="text-xs text-gray-600">Actions taken:</span>
                    </div>
                    <div className="space-y-1">
                      {activity.function_calls.map((call, index) => (
                        <div key={index} className="text-xs bg-white p-2 rounded border">
                          <span className="font-medium text-gray-900">{call.name}</span>
                          {call.parameters && (
                            <div className="text-gray-600 mt-1">
                              Platform: {call.parameters.platform || 'Unknown'}
                              {call.parameters.restaurant_name && (
                                <span className="ml-2">
                                  Restaurant: {call.parameters.restaurant_name}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* MCP results */}
                {activity.mcp_results && activity.mcp_results.length > 0 && (
                  <div>
                    <div className="flex items-center space-x-2 mb-1">
                      <MessageSquare className="w-3 h-3 text-gray-500" />
                      <span className="text-xs text-gray-600">Results:</span>
                    </div>
                    <div className="flex space-x-2">
                      {activity.mcp_results.map((result, index) => (
                        <span 
                          key={index}
                          className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                            result.success 
                              ? 'bg-success-100 text-success-800' 
                              : 'bg-danger-100 text-danger-800'
                          }`}
                        >
                          {result.platform}: {result.success ? 'Success' : 'Failed'}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
            
            {/* Voice activity indicator for active sessions */}
            {isVoiceInput && (
              <div className="flex items-center space-x-2 mt-2">
                <VoiceWaveform isActive={true} />
                <span className="text-xs text-gray-500">Processing voice...</span>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <Activity className="w-5 h-5 mr-2" />
          Voice Activity Feed
          {selectedSession && (
            <span className="ml-2 text-sm font-normal text-gray-600">
              (Session: {selectedSession.slice(0, 8)}...)
            </span>
          )}
        </h2>
        <div className="flex items-center space-x-2">
          <span className="text-sm text-gray-600">
            {activities.length} activities
          </span>
          <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></div>
        </div>
      </div>

      <div className="space-y-3 max-h-96 overflow-y-auto scrollbar-hide">
        {activities.length === 0 ? (
          <div className="text-center py-8">
            <Mic className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">No voice activity yet</h3>
            <p className="text-gray-600">
              {selectedSession 
                ? 'No voice activity found for this session'
                : 'Voice interactions will appear here in real-time'
              }
            </p>
          </div>
        ) : (
          activities.map((activity) => (
            <ActivityItem key={activity.id} activity={activity} />
          ))
        )}
      </div>

      {/* Live indicator */}
      {activities.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-600">
            <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></div>
            <span>Live updates enabled</span>
          </div>
        </div>
      )}
    </div>
  );
};

export default VoiceActivity;
