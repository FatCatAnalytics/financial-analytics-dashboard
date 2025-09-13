import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { 
  Database, 
  Clock, 
  TrendingUp, 
  Activity, 
  CheckCircle2, 
  AlertCircle,
  RefreshCw,
  Calendar,
  BarChart3,
  DollarSign
} from 'lucide-react';

interface StatusDashboardProps {
  isConnected: boolean;
  isConnecting: boolean;
  connectionError?: string;
  lastConnectionTime?: Date;
  lastDataUpdate?: Date;
  recordCount?: number;
  latestPeriod?: string;
  totalCommitment?: number;
  onRefresh?: () => void;
}

export function StatusDashboard({
  isConnected,
  isConnecting,
  connectionError,
  lastConnectionTime,
  lastDataUpdate,
  recordCount = 0,
  latestPeriod,
  totalCommitment
}: StatusDashboardProps) {
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      notation: 'compact',
      maximumFractionDigits: 1
    }).format(value);
  };

  const getDataFreshnessStatus = () => {
    if (!latestPeriod) return { label: 'No data', color: 'text-muted-foreground', variant: 'secondary' as const };
    
    // Parse the latest period (format: "Aug 2024" or YYYYMMDD string)
    let latestDate: Date;
    
    if (latestPeriod.includes(' ')) {
      // Format like "Aug 2024"
      latestDate = new Date(latestPeriod);
    } else {
      // YYYYMMDD format
      const year = parseInt(latestPeriod.substring(0, 4));
      const month = parseInt(latestPeriod.substring(4, 6)) - 1; // Month is 0-indexed
      const day = parseInt(latestPeriod.substring(6, 8));
      latestDate = new Date(year, month, day);
    }
    
    const now = new Date();
    const oneMonthAgo = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
    
    if (latestDate >= oneMonthAgo) {
      return { label: 'Fresh', color: 'text-green-600', variant: 'default' as const };
    } else {
      return { label: 'Stale', color: 'text-amber-600', variant: 'outline' as const };
    }
  };

  const dataStatus = getDataFreshnessStatus();

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Database Connection Status */}
      <Card className={`relative overflow-hidden ${
        isConnected ? 'border-emerald-200 bg-gradient-to-br from-emerald-50 to-green-50' : 
        connectionError ? 'border-red-200 bg-gradient-to-br from-red-50 to-rose-50' :
        'border-amber-200 bg-gradient-to-br from-amber-50 to-yellow-50'
      }`}>
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${
                isConnected ? 'bg-green-100' : 
                connectionError ? 'bg-red-100' : 'bg-amber-100'
              }`}>
                {isConnecting ? (
                  <RefreshCw className="w-4 h-4 text-amber-600 animate-spin" />
                ) : isConnected ? (
                  <Database className="w-4 h-4 text-green-600" />
                ) : (
                  <AlertCircle className="w-4 h-4 text-red-600" />
                )}
              </div>
              <div>
                <p className="text-sm font-medium">Database</p>
                <p className={`text-xs ${
                  isConnected ? 'text-green-600' : 
                  connectionError ? 'text-red-600' : 'text-amber-600'
                }`}>
                  {isConnecting ? 'Connecting...' : 
                   isConnected ? 'Connected' : 'Disconnected'}
                </p>
              </div>
            </div>
            {isConnected && (
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            )}
          </div>
          {lastConnectionTime && (
            <p className="text-xs text-muted-foreground mt-2">
              Last sync: {lastConnectionTime.toLocaleTimeString()}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Data Freshness */}
      <Card className="relative overflow-hidden bg-gradient-to-br from-blue-50 to-indigo-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-blue-100">
                <Clock className="w-4 h-4 text-blue-600" />
              </div>
              <div>
                <p className="text-sm font-medium">Data Freshness</p>
                <Badge variant={dataStatus.variant} className="text-xs mt-1">
                  {dataStatus.label}
                </Badge>
              </div>
            </div>
            <Activity className="w-5 h-5 text-blue-500" />
          </div>
          {lastDataUpdate && (
            <p className="text-xs text-muted-foreground mt-2">
              Updated: {lastDataUpdate.toLocaleString()}
            </p>
          )}
        </CardContent>
      </Card>

      {/* Latest Period */}
      <Card className="relative overflow-hidden bg-gradient-to-br from-purple-50 to-violet-50 border-purple-200">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-purple-100">
                <Calendar className="w-4 h-4 text-purple-600" />
              </div>
              <div>
                <p className="text-sm font-medium">Latest Period</p>
                <p className="text-sm font-semibold text-purple-700">
                  {latestPeriod || 'No data'}
                </p>
              </div>
            </div>
            <TrendingUp className="w-5 h-5 text-purple-500" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            {recordCount} records available
          </p>
        </CardContent>
      </Card>

      {/* Total Portfolio */}
      <Card className="relative overflow-hidden bg-gradient-to-br from-emerald-50 to-teal-50 border-emerald-200">
        <CardContent className="p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-emerald-100">
                <DollarSign className="w-4 h-4 text-emerald-600" />
              </div>
              <div>
                <p className="text-sm font-medium">Portfolio Value</p>
                <p className="text-sm font-semibold text-emerald-700">
                  {totalCommitment && totalCommitment > 0 ? formatCurrency(totalCommitment) : 'No data'}
                </p>
              </div>
            </div>
            <BarChart3 className="w-5 h-5 text-emerald-500" />
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Current commitment amount
          </p>
        </CardContent>
      </Card>
    </div>
  );
}