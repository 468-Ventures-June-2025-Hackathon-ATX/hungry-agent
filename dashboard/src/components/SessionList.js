import React from 'react';
import { 
  Users, 
  User, 
  Clock, 
  CheckCircle, 
  XCircle,
  Activity
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const SessionList = ({ sessions, selectedSession, onSelectSession }) => {
  const getSessionStatusIcon = (session) => {
    if (session.is_active) {
      return <div className="w-2 h-2 bg-success-500 rounded-full animate-pulse"></div>;
    } else {
      return <div className="w-2 h-2 bg-gray-400 rounded-full"></div>;
    }
  };

  const getSessionStats = (session) => {
    const successRate = session.total_interactions > 0 
      ? Math.round((session.successful_orders / session.total_interactions) * 100)
      : 0;
    
    return {
      successRate,
      totalOrders: session.successful_orders + session.failed_orders
    };
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <Users className="w-5 h-5 mr-2" />
          Voice Sessions
        </h2>
        <span className="text-sm text-gray-600">
          {sessions.filter(s => s.is_active).length} active
        </span>
      </div>

      <div className="space-y-2 max-h-80 overflow-y-auto scrollbar-hide">
        {sessions.length === 0 ? (
          <div className="text-center py-6">
            <User className="w-8 h-8 text-gray-400 mx-auto mb-2" />
            <p className="text-sm text-gray-600">No sessions yet</p>
          </div>
        ) : (
          <>
            {/* Show all sessions option */}
            <button
              onClick={() => onSelectSession(null)}
              className={`w-full text-left p-3 rounded-lg border transition-colors ${
                selectedSession === null
                  ? 'border-primary-200 bg-primary-50 text-primary-900'
                  : 'border-gray-200 bg-white hover:bg-gray-50 text-gray-900'
              }`}
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <Users className="w-4 h-4" />
                  <span className="font-medium">All Sessions</span>
                </div>
                <span className="text-xs text-gray-500">
                  {sessions.length} total
                </span>
              </div>
            </button>

            {/* Individual sessions */}
            {sessions.map((session) => {
              const stats = getSessionStats(session);
              const isSelected = selectedSession === session.session_id;
              
              return (
                <button
                  key={session.session_id}
                  onClick={() => onSelectSession(session.session_id)}
                  className={`w-full text-left p-3 rounded-lg border transition-colors ${
                    isSelected
                      ? 'border-primary-200 bg-primary-50 text-primary-900'
                      : 'border-gray-200 bg-white hover:bg-gray-50 text-gray-900'
                  }`}
                >
                  <div className="space-y-2">
                    {/* Session header */}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {getSessionStatusIcon(session)}
                        <span className="font-medium text-sm">
                          {session.session_id.slice(0, 8)}...
                        </span>
                      </div>
                      <span className={`text-xs px-2 py-1 rounded-full ${
                        session.is_active 
                          ? 'bg-success-100 text-success-800' 
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {session.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </div>

                    {/* Session stats */}
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="text-center">
                        <div className="font-medium text-gray-900">
                          {session.total_interactions}
                        </div>
                        <div className="text-gray-500">Interactions</div>
                      </div>
                      <div className="text-center">
                        <div className="font-medium text-gray-900">
                          {stats.totalOrders}
                        </div>
                        <div className="text-gray-500">Orders</div>
                      </div>
                      <div className="text-center">
                        <div className={`font-medium ${
                          stats.successRate >= 80 ? 'text-success-600' :
                          stats.successRate >= 60 ? 'text-warning-600' : 'text-danger-600'
                        }`}>
                          {stats.successRate}%
                        </div>
                        <div className="text-gray-500">Success</div>
                      </div>
                    </div>

                    {/* Timing info */}
                    <div className="flex items-center justify-between text-xs text-gray-500">
                      <div className="flex items-center space-x-1">
                        <Clock className="w-3 h-3" />
                        <span>
                          Started {formatDistanceToNow(new Date(session.started_at), { addSuffix: true })}
                        </span>
                      </div>
                      {session.is_active && (
                        <div className="flex items-center space-x-1">
                          <Activity className="w-3 h-3" />
                          <span>
                            {formatDistanceToNow(new Date(session.last_activity), { addSuffix: true })}
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Success/failure indicators */}
                    {stats.totalOrders > 0 && (
                      <div className="flex items-center space-x-2 text-xs">
                        {session.successful_orders > 0 && (
                          <div className="flex items-center space-x-1 text-success-600">
                            <CheckCircle className="w-3 h-3" />
                            <span>{session.successful_orders} successful</span>
                          </div>
                        )}
                        {session.failed_orders > 0 && (
                          <div className="flex items-center space-x-1 text-danger-600">
                            <XCircle className="w-3 h-3" />
                            <span>{session.failed_orders} failed</span>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </button>
              );
            })}
          </>
        )}
      </div>

      {/* Session summary */}
      {sessions.length > 0 && (
        <div className="mt-4 pt-4 border-t border-gray-200">
          <div className="grid grid-cols-2 gap-4 text-center text-xs">
            <div>
              <div className="font-medium text-gray-900">
                {sessions.filter(s => s.is_active).length}
              </div>
              <div className="text-gray-500">Active Now</div>
            </div>
            <div>
              <div className="font-medium text-gray-900">
                {sessions.reduce((sum, s) => sum + s.total_interactions, 0)}
              </div>
              <div className="text-gray-500">Total Interactions</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SessionList;
