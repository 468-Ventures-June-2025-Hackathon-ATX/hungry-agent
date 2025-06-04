import React, { useState, useEffect } from 'react';
import { 
  Package, 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle,
  RefreshCw,
  MapPin,
  Search
} from 'lucide-react';

const BatchOrderStatus = ({ socket }) => {
  const [batchOrders, setBatchOrders] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (socket) {
      const handleMessage = (event) => {
        try {
          const update = JSON.parse(event.data);
          if (update.type === 'batch_order_created' || update.type === 'batch_order_placed') {
            console.log('Batch order update:', update);
            fetchBatchOrders();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message in BatchOrderStatus:', error);
        }
      };

      socket.addEventListener('message', handleMessage);

      // Initial fetch
      fetchBatchOrders();

      return () => {
        socket.removeEventListener('message', handleMessage);
      };
    }
  }, [socket]);

  const fetchBatchOrders = async () => {
    try {
      setLoading(true);
      // Try to fetch from the dashboard-test session first, then fallback to batch-test-austin
      let response = await fetch('/api/batch/orders/dashboard-test');
      if (!response.ok) {
        response = await fetch('/api/batch/orders/batch-test-austin');
      }
      if (response.ok) {
        const data = await response.json();
        setBatchOrders(data.orders || []);
      }
    } catch (error) {
      console.error('Error fetching batch orders:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-4 h-4 text-gray-500" />;
      case 'searching':
      case 'search_started':
        return <Search className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'results_ready':
      case 'ready_to_order':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'order_placed':
        return <Package className="w-4 h-4 text-success-500" />;
      case 'search_failed':
      case 'order_failed':
      case 'error':
        return <XCircle className="w-4 h-4 text-danger-500" />;
      case 'cancelled':
        return <XCircle className="w-4 h-4 text-gray-500" />;
      default:
        return <AlertCircle className="w-4 h-4 text-warning-500" />;
    }
  };

  const getStatusBadge = (status) => {
    const baseClasses = "px-2 py-1 text-xs font-medium rounded-full";
    
    switch (status) {
      case 'pending':
        return <span className={`${baseClasses} bg-gray-100 text-gray-800`}>Pending</span>;
      case 'searching':
      case 'search_started':
        return <span className={`${baseClasses} bg-blue-100 text-blue-800`}>Searching</span>;
      case 'results_ready':
      case 'ready_to_order':
        return <span className={`${baseClasses} bg-green-100 text-green-800`}>Ready</span>;
      case 'order_placed':
        return <span className={`${baseClasses} bg-success-100 text-success-800`}>Ordered</span>;
      case 'search_failed':
      case 'order_failed':
      case 'error':
        return <span className={`${baseClasses} bg-danger-100 text-danger-800`}>Failed</span>;
      case 'cancelled':
        return <span className={`${baseClasses} bg-gray-100 text-gray-800`}>Cancelled</span>;
      default:
        return <span className={`${baseClasses} bg-warning-100 text-warning-800`}>Unknown</span>;
    }
  };

  const formatTimeAgo = (timestamp) => {
    const now = new Date();
    const created = new Date(timestamp);
    const diffMs = now - created;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    return created.toLocaleDateString();
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-lg font-semibold text-gray-900 flex items-center">
          <Package className="w-5 h-5 mr-2" />
          Batch Orders
        </h2>
        <button
          onClick={fetchBatchOrders}
          disabled={loading}
          className="btn btn-sm btn-outline"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {batchOrders.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Package className="w-12 h-12 mx-auto mb-4 text-gray-300" />
          <p>No batch orders found</p>
          <p className="text-sm">Create a batch order by saying "Order tacos, pizza, and burgers"</p>
        </div>
      ) : (
        <div className="space-y-4">
          {batchOrders.map((order) => (
            <div key={order.order_id} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center space-x-3">
                  {getStatusIcon(order.status)}
                  <div>
                    <h3 className="font-medium text-gray-900 capitalize">
                      {order.restaurant_query}
                    </h3>
                    <p className="text-sm text-gray-600">
                      {order.items.join(', ')}
                    </p>
                  </div>
                </div>
                {getStatusBadge(order.status)}
              </div>

              <div className="flex items-center justify-between text-sm text-gray-600">
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-1">
                    <MapPin className="w-3 h-3" />
                    <span>{order.location}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Clock className="w-3 h-3" />
                    <span>{formatTimeAgo(order.created_at)}</span>
                  </div>
                </div>
                <div className="text-xs text-gray-500">
                  ID: {order.order_id.split('_').pop()}
                </div>
              </div>

              {order.search_results && order.search_results.results && (
                <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                  <h4 className="text-sm font-medium text-gray-900 mb-2">Search Results</h4>
                  <div className="text-sm text-gray-600">
                    {typeof order.search_results.results === 'string' 
                      ? order.search_results.results 
                      : JSON.stringify(order.search_results.results, null, 2)
                    }
                  </div>
                </div>
              )}

              {order.status === 'ready_to_order' && (
                <div className="mt-3 pt-3 border-t border-gray-200">
                  <button className="btn btn-sm btn-primary">
                    Place Order
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default BatchOrderStatus;
