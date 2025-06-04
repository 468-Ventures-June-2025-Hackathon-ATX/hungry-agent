import React, { useState } from 'react';
import { 
  Clock, 
  CheckCircle, 
  XCircle, 
  AlertCircle, 
  Truck, 
  MapPin,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

const OrderCard = ({ order, onStatusUpdate }) => {
  const [expanded, setExpanded] = useState(false);

  const getStatusInfo = (status) => {
    switch (status) {
      case 'pending':
        return {
          icon: <Clock className="w-4 h-4" />,
          color: 'warning',
          label: 'Pending'
        };
      case 'processing':
        return {
          icon: <AlertCircle className="w-4 h-4" />,
          color: 'primary',
          label: 'Processing'
        };
      case 'confirmed':
        return {
          icon: <CheckCircle className="w-4 h-4" />,
          color: 'success',
          label: 'Confirmed'
        };
      case 'preparing':
        return {
          icon: <Clock className="w-4 h-4" />,
          color: 'warning',
          label: 'Preparing'
        };
      case 'out_for_delivery':
        return {
          icon: <Truck className="w-4 h-4" />,
          color: 'primary',
          label: 'Out for Delivery'
        };
      case 'delivered':
        return {
          icon: <CheckCircle className="w-4 h-4" />,
          color: 'success',
          label: 'Delivered'
        };
      case 'cancelled':
        return {
          icon: <XCircle className="w-4 h-4" />,
          color: 'danger',
          label: 'Cancelled'
        };
      case 'failed':
        return {
          icon: <XCircle className="w-4 h-4" />,
          color: 'danger',
          label: 'Failed'
        };
      default:
        return {
          icon: <AlertCircle className="w-4 h-4" />,
          color: 'warning',
          label: 'Unknown'
        };
    }
  };

  const getPlatformInfo = (platform) => {
    switch (platform) {
      case 'uber_eats':
        return {
          name: 'Uber Eats',
          color: 'bg-black text-white',
          borderColor: 'border-l-black'
        };
      case 'doordash':
        return {
          name: 'DoorDash',
          color: 'bg-red-500 text-white',
          borderColor: 'border-l-red-500'
        };
      default:
        return {
          name: platform,
          color: 'bg-gray-500 text-white',
          borderColor: 'border-l-gray-500'
        };
    }
  };

  const statusInfo = getStatusInfo(order.status);
  const platformInfo = getPlatformInfo(order.platform);

  const handleStatusChange = (newStatus) => {
    onStatusUpdate(order.id, newStatus);
  };

  const getItemsText = () => {
    if (!order.items || order.items.length === 0) {
      return 'No items';
    }

    const totalItems = order.items.reduce((sum, item) => sum + (item.quantity || 1), 0);
    const firstItem = order.items[0];
    
    if (order.items.length === 1) {
      return `${firstItem.quantity || 1}x ${firstItem.name}`;
    } else {
      return `${totalItems} items (${firstItem.name}${order.items.length > 1 ? ` +${order.items.length - 1} more` : ''})`;
    }
  };

  return (
    <div 
      className={`order-card bg-white rounded-lg border border-gray-200 ${platformInfo.borderColor} shadow-sm hover:shadow-md transition-all duration-200`}
      data-session={order.session_id}
    >
      <div className="p-4">
        {/* Header */}
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              <span className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${platformInfo.color}`}>
                {platformInfo.name}
              </span>
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center space-x-2">
                <h3 className="text-sm font-medium text-gray-900 truncate">
                  {order.restaurant_name || 'Unknown Restaurant'}
                </h3>
                <span className="text-xs text-gray-500">
                  #{order.id}
                </span>
              </div>
              <p className="text-sm text-gray-600 mt-1">
                {getItemsText()}
              </p>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium badge-${statusInfo.color}`}>
              {statusInfo.icon}
              <span className="ml-1">{statusInfo.label}</span>
            </span>
          </div>
        </div>

        {/* Metadata */}
        <div className="flex items-center justify-between text-xs text-gray-500 mb-3">
          <div className="flex items-center space-x-4">
            <span>
              Session: {order.session_id?.slice(0, 8)}...
            </span>
            <span>
              {formatDistanceToNow(new Date(order.created_at), { addSuffix: true })}
            </span>
          </div>
          
          {order.total_amount && (
            <span className="font-medium text-gray-900">
              ${order.total_amount.toFixed(2)}
            </span>
          )}
        </div>

        {/* Delivery address */}
        {order.delivery_address && (
          <div className="flex items-center space-x-2 text-xs text-gray-600 mb-3">
            <MapPin className="w-3 h-3" />
            <span className="truncate">{order.delivery_address}</span>
          </div>
        )}

        {/* Expandable details */}
        <div className="border-t border-gray-100 pt-3">
          <button
            onClick={() => setExpanded(!expanded)}
            className="flex items-center justify-between w-full text-sm text-gray-600 hover:text-gray-900"
          >
            <span>
              {expanded ? 'Hide details' : 'Show details'}
            </span>
            {expanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {expanded && (
            <div className="mt-3 space-y-3 animate-slide-up">
              {/* Items list */}
              {order.items && order.items.length > 0 && (
                <div>
                  <h4 className="text-xs font-medium text-gray-700 mb-2">Items:</h4>
                  <div className="space-y-1">
                    {order.items.map((item, index) => (
                      <div key={index} className="flex justify-between text-xs">
                        <span className="text-gray-600">
                          {item.quantity || 1}x {item.name}
                          {item.customizations && item.customizations.length > 0 && (
                            <span className="text-gray-500 ml-1">
                              ({item.customizations.join(', ')})
                            </span>
                          )}
                        </span>
                        {item.price && (
                          <span className="text-gray-900 font-medium">
                            ${(item.price * (item.quantity || 1)).toFixed(2)}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* External order ID */}
              {order.external_order_id && (
                <div>
                  <span className="text-xs text-gray-500">
                    External ID: {order.external_order_id}
                  </span>
                </div>
              )}

              {/* Status update buttons */}
              <div>
                <h4 className="text-xs font-medium text-gray-700 mb-2">Update Status:</h4>
                <div className="flex flex-wrap gap-1">
                  {['confirmed', 'preparing', 'out_for_delivery', 'delivered', 'cancelled'].map((status) => (
                    <button
                      key={status}
                      onClick={() => handleStatusChange(status)}
                      disabled={order.status === status}
                      className={`px-2 py-1 text-xs rounded ${
                        order.status === status
                          ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                          : 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
                      }`}
                    >
                      {getStatusInfo(status).label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tracking URL */}
              {order.tracking_url && (
                <div>
                  <a
                    href={order.tracking_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-primary-600 hover:text-primary-700 underline"
                  >
                    Track Order →
                  </a>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default OrderCard;
