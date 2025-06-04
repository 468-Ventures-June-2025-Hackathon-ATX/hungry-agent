import React from 'react';
import { 
  ShoppingCart, 
  TrendingUp, 
  Clock, 
  CheckCircle,
  DollarSign,
  Activity
} from 'lucide-react';

const OrderStats = ({ orders }) => {
  // Calculate statistics
  const stats = React.useMemo(() => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    
    // Filter orders by time periods
    const todayOrders = orders.filter(order => 
      new Date(order.created_at) >= today
    );
    
    const thisHourOrders = orders.filter(order => {
      const orderTime = new Date(order.created_at);
      return orderTime >= new Date(now.getTime() - 60 * 60 * 1000);
    });
    
    // Status counts
    const statusCounts = orders.reduce((acc, order) => {
      acc[order.status] = (acc[order.status] || 0) + 1;
      return acc;
    }, {});
    
    // Platform distribution
    const platformCounts = orders.reduce((acc, order) => {
      acc[order.platform] = (acc[order.platform] || 0) + 1;
      return acc;
    }, {});
    
    // Revenue calculation (if available)
    const totalRevenue = orders.reduce((sum, order) => 
      sum + (order.total_amount || 0), 0
    );
    
    const todayRevenue = todayOrders.reduce((sum, order) => 
      sum + (order.total_amount || 0), 0
    );
    
    // Success rate
    const completedOrders = orders.filter(order => 
      order.status === 'delivered'
    ).length;
    
    const failedOrders = orders.filter(order => 
      ['cancelled', 'failed'].includes(order.status)
    ).length;
    
    const successRate = orders.length > 0 
      ? Math.round((completedOrders / orders.length) * 100)
      : 0;
    
    // Average order value
    const ordersWithAmount = orders.filter(order => order.total_amount > 0);
    const avgOrderValue = ordersWithAmount.length > 0
      ? ordersWithAmount.reduce((sum, order) => sum + order.total_amount, 0) / ordersWithAmount.length
      : 0;
    
    return {
      total: orders.length,
      today: todayOrders.length,
      thisHour: thisHourOrders.length,
      completed: completedOrders,
      failed: failedOrders,
      successRate,
      totalRevenue,
      todayRevenue,
      avgOrderValue,
      statusCounts,
      platformCounts
    };
  }, [orders]);

  const StatCard = ({ icon, title, value, subtitle, color = 'primary' }) => (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="flex items-center">
        <div className={`flex-shrink-0 p-2 rounded-lg bg-${color}-100`}>
          <div className={`w-6 h-6 text-${color}-600`}>
            {icon}
          </div>
        </div>
        <div className="ml-4 flex-1">
          <div className="text-2xl font-bold text-gray-900">
            {value}
          </div>
          <div className="text-sm font-medium text-gray-700">
            {title}
          </div>
          {subtitle && (
            <div className="text-xs text-gray-500 mt-1">
              {subtitle}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const PlatformBreakdown = () => (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <Activity className="w-5 h-5 mr-2" />
        Platform Distribution
      </h3>
      
      <div className="space-y-3">
        {Object.entries(stats.platformCounts).map(([platform, count]) => {
          const percentage = Math.round((count / stats.total) * 100);
          const platformInfo = platform === 'uber_eats' 
            ? { name: 'Uber Eats', color: 'bg-black' }
            : { name: 'DoorDash', color: 'bg-red-500' };
          
          return (
            <div key={platform} className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                <div className={`w-3 h-3 rounded-full ${platformInfo.color}`}></div>
                <span className="text-sm font-medium text-gray-900">
                  {platformInfo.name}
                </span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">{count} orders</span>
                <span className="text-xs text-gray-500">({percentage}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  const StatusBreakdown = () => (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
        <CheckCircle className="w-5 h-5 mr-2" />
        Order Status
      </h3>
      
      <div className="space-y-2">
        {Object.entries(stats.statusCounts).map(([status, count]) => {
          const percentage = Math.round((count / stats.total) * 100);
          const statusInfo = {
            'pending': { label: 'Pending', color: 'bg-warning-500' },
            'processing': { label: 'Processing', color: 'bg-primary-500' },
            'confirmed': { label: 'Confirmed', color: 'bg-success-500' },
            'preparing': { label: 'Preparing', color: 'bg-warning-500' },
            'out_for_delivery': { label: 'Out for Delivery', color: 'bg-primary-500' },
            'delivered': { label: 'Delivered', color: 'bg-success-500' },
            'cancelled': { label: 'Cancelled', color: 'bg-gray-500' },
            'failed': { label: 'Failed', color: 'bg-danger-500' }
          }[status] || { label: status, color: 'bg-gray-500' };
          
          return (
            <div key={status} className="flex items-center justify-between text-sm">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${statusInfo.color}`}></div>
                <span className="text-gray-900">{statusInfo.label}</span>
              </div>
              <div className="flex items-center space-x-2">
                <span className="text-gray-600">{count}</span>
                <span className="text-gray-500">({percentage}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Main stats grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={<ShoppingCart />}
          title="Total Orders"
          value={stats.total}
          subtitle={`${stats.today} today`}
          color="primary"
        />
        
        <StatCard
          icon={<TrendingUp />}
          title="Success Rate"
          value={`${stats.successRate}%`}
          subtitle={`${stats.completed} completed`}
          color="success"
        />
        
        <StatCard
          icon={<Clock />}
          title="This Hour"
          value={stats.thisHour}
          subtitle="Recent activity"
          color="warning"
        />
        
        <StatCard
          icon={<DollarSign />}
          title="Avg Order Value"
          value={stats.avgOrderValue > 0 ? `$${stats.avgOrderValue.toFixed(2)}` : 'N/A'}
          subtitle={stats.totalRevenue > 0 ? `$${stats.totalRevenue.toFixed(2)} total` : 'No revenue data'}
          color="success"
        />
      </div>

      {/* Detailed breakdowns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <PlatformBreakdown />
        <StatusBreakdown />
      </div>

      {/* Quick insights */}
      {stats.total > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <h3 className="text-lg font-semibold text-gray-900 mb-3">Quick Insights</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="font-medium text-gray-900">
                {Math.round((stats.today / stats.total) * 100)}%
              </div>
              <div className="text-gray-600">of orders today</div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="font-medium text-gray-900">
                {stats.failed > 0 ? Math.round((stats.failed / stats.total) * 100) : 0}%
              </div>
              <div className="text-gray-600">failure rate</div>
            </div>
            
            <div className="text-center p-3 bg-gray-50 rounded-lg">
              <div className="font-medium text-gray-900">
                {Object.keys(stats.platformCounts).length}
              </div>
              <div className="text-gray-600">platforms used</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default OrderStats;
