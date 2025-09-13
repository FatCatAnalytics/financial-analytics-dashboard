import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Table2, BarChart3, Filter, RefreshCw, AlertCircle } from 'lucide-react';
import { FilterPanel } from './components/FilterPanel';
import { DataTable } from './components/DataTable';
import { ChartVisualization } from './components/ChartVisualization';
import { ConnectionStatus, ConnectionCard } from './components/ConnectionStatus';
import { LoadingOverlay, FilterLoadingSkeleton, DataLoadingSkeleton, ChartLoadingSkeleton } from './components/LoadingOverlay';
import { StatusDashboard } from './components/StatusDashboard';
import { apiService, type AnalyticsRecord } from './services/api';
import type { SelectedFilters, AnalyticsData, CustomCommitmentRange } from './types/data';

export default function App() {
  const [selectedFilters, setSelectedFilters] = useState<SelectedFilters>({
    lineOfBusiness: [],
    commitmentSizeGroup: [],
    customCommitmentRanges: [],
    riskGroup: [],
    bankId: [],
    region: [],
    naicsGrpName: []
  });

  const [queryResults, setQueryResults] = useState<AnalyticsData[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [hasRunQuery, setHasRunQuery] = useState(false);
  
  // Connection and loading states
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(true);
  const [connectionError, setConnectionError] = useState<string | null>(null);
  const [lastConnectionTime, setLastConnectionTime] = useState<Date | null>(null);
  const [isLoadingFilters, setIsLoadingFilters] = useState(true);
  const [queryProgress, setQueryProgress] = useState<string>('');
  const [lastDataUpdate, setLastDataUpdate] = useState<Date | null>(null);
  const [filterOptions, setFilterOptions] = useState<any>(null);

  const handleFilterChange = (filterType: keyof SelectedFilters, values: string[]) => {
    setSelectedFilters(prev => ({
      ...prev,
      [filterType]: values
    }));
  };

  const handleCustomRangeAdd = (range: CustomCommitmentRange) => {
    setSelectedFilters(prev => ({
      ...prev,
      customCommitmentRanges: [...prev.customCommitmentRanges, range]
    }));
  };

  const handleCustomRangeRemove = (id: string) => {
    setSelectedFilters(prev => ({
      ...prev,
      customCommitmentRanges: prev.customCommitmentRanges.filter(range => range.id !== id)
    }));
  };

  const handleClearFilters = () => {
    setSelectedFilters({
      lineOfBusiness: [],
      commitmentSizeGroup: [],
      customCommitmentRanges: [],
      riskGroup: [],
      bankId: [],
      region: [],
      naicsGrpName: []
    });
  };

  // Connect to database on mount
  useEffect(() => {
    const connectToDatabase = async () => {
      setIsConnecting(true);
      
      try {
        // Test the actual database connection
        const connectionStatus = await apiService.getConnectionStatus();
        
        if (connectionStatus.isConnected) {
          setIsConnected(true);
          setConnectionError(null);
          setLastConnectionTime(new Date(connectionStatus.lastConnectionTime || new Date().toISOString()));
          
          // Load filter options after successful connection
          await loadFilterOptions();
        } else {
          throw new Error(connectionStatus.error || 'Unable to connect to PostgreSQL database');
        }
        
      } catch (error) {
        setConnectionError(error instanceof Error ? error.message : 'Connection failed');
        setIsConnected(false);
      } finally {
        setIsConnecting(false);
      }
    };

    connectToDatabase();
  }, []);

  const loadFilterOptions = async () => {
    setIsLoadingFilters(true);
    
    try {
      // Load actual filter options from database
      const options = await apiService.getFilterOptions();
      setFilterOptions(options);
      setIsLoadingFilters(false);
    } catch (error) {
      setIsLoadingFilters(false);
      console.error('Failed to load filter options:', error);
      // Fallback to empty options
      setFilterOptions({
        lineOfBusiness: [],
        commitmentSizeGroup: [],
        riskGroup: [],
        bankId: [],
        region: [],
        naicsGrpName: []
      });
    }
  };

  const handleRetryConnection = async () => {
    setConnectionError(null);
    setIsConnecting(true);
    
    try {
      // Test the actual database connection
      const connectionStatus = await apiService.getConnectionStatus();
      
      if (connectionStatus.isConnected) {
        setIsConnected(true);
        setLastConnectionTime(new Date(connectionStatus.lastConnectionTime || new Date().toISOString()));
        await loadFilterOptions();
      } else {
        throw new Error(connectionStatus.error || 'Unable to connect to PostgreSQL database');
      }
    } catch (error) {
      setConnectionError(error instanceof Error ? error.message : 'Connection failed');
      setIsConnected(false);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleRunQuery = async () => {
    if (!isConnected) {
      return;
    }

    setIsLoading(true);
    
    try {
      // Use the API service to simulate query execution with progress updates
      const analyticsData = await apiService.simulateQueryExecution(
        {
          filters: selectedFilters,
          limit: 1000
        },
        (message: string) => {
          setQueryProgress(message);
        }
      );
      
      // Convert AnalyticsRecord[] to AnalyticsData[] format expected by frontend
      const convertedData: AnalyticsData[] = analyticsData.map(record => ({
        ProcessingDateKey: record.ProcessingDateKey,
        CommitmentAmt: record.CommitmentAmt,
        Deals: record.Deals,
        OutstandingAmt: record.OutstandingAmt,
        ProcessingDateKeyPrior: record.ProcessingDateKeyPrior,
        CommitmentAmtPrior: record.CommitmentAmtPrior,
        OutstandingAmtPrior: record.OutstandingAmtPrior,
        DealsPrior: record.DealsPrior,
        ca_diff: record.ca_diff,
        oa_diff: record.oa_diff,
        deals_diff: record.deals_diff,
        ca_model_diff: record.ca_model_diff,
        oa_model_diff: record.oa_model_diff,
        deals_model_diff: record.deals_model_diff
      }));
      
      setQueryResults(convertedData);
      setHasRunQuery(true);
      setQueryProgress('');
      setLastDataUpdate(new Date());
      
    } catch (error) {
      console.error('Query failed:', error);
      setQueryProgress('Query failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const totalSelectedFilters = Object.entries(selectedFilters).reduce((acc, [key, value]) => {
    if (key === 'customCommitmentRanges') {
      return acc + (value as CustomCommitmentRange[]).length;
    }
    return acc + (value as string[]).length;
  }, 0);

  // Get latest period from data (ProcessingDateKey is YYYYMMDD format)
  const getLatestPeriod = () => {
    if (queryResults.length === 0) return 'Aug 2024';
    const latest = queryResults[queryResults.length - 1];
    const dateStr = latest.ProcessingDateKey.toString();
    
    // Parse YYYYMMDD format
    if (dateStr.length === 8) {
      const year = dateStr.substring(0, 4);
      const month = dateStr.substring(4, 6);
      const day = dateStr.substring(6, 8);
      const date = new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }
    
    return 'Aug 2024'; // fallback
  };

  // Calculate total commitment from latest data
  const getTotalCommitment = () => {
    if (queryResults.length === 0) return 21284739215; // Default value
    return queryResults[queryResults.length - 1]?.CommitmentAmt || 0;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-slate-100/30 to-blue-50/20">
      <div className="container mx-auto p-6 space-y-8">
        {/* Header */}
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-slate-600/5 to-blue-600/5 rounded-3xl" />
          <div className="relative bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-3xl p-8 shadow-xl shadow-slate-500/10">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <div className="flex items-center gap-3">
                  <div className="p-3 bg-gradient-to-br from-slate-700 to-blue-700 rounded-2xl">
                    <BarChart3 className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-3xl font-bold bg-gradient-to-r from-slate-700 to-blue-700 bg-clip-text text-transparent">
                      Financial Analytics Dashboard
                    </h1>
                    <p className="text-muted-foreground text-lg">
                      Analyze commitment amounts, deals, and outstanding amounts with advanced filtering
                    </p>
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <ConnectionStatus
                  isConnected={isConnected}
                  isConnecting={isConnecting}
                  connectionType="database"
                  lastConnectionTime={lastConnectionTime || undefined}
                  error={connectionError || undefined}
                />
                <Badge variant="outline" className="px-3 py-1.5 bg-white/50">
                  <Filter className="w-4 h-4 mr-2" />
                  {totalSelectedFilters} filters active
                </Badge>
                {!isConnecting && connectionError && (
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={handleRetryConnection}
                    className="flex items-center gap-2 bg-white/50 hover:bg-white/80"
                  >
                    <RefreshCw className="w-4 h-4" />
                    Retry Connection
                  </Button>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Status Dashboard */}
        <StatusDashboard
          isConnected={isConnected}
          isConnecting={isConnecting}
          connectionError={connectionError || undefined}
          lastConnectionTime={lastConnectionTime || undefined}
          lastDataUpdate={lastDataUpdate || undefined}
          recordCount={queryResults.length}
          latestPeriod={getLatestPeriod()}
          totalCommitment={getTotalCommitment()}
          onRefresh={handleRetryConnection}
        />

        {/* Connection Status Card (shown when there are issues) */}
        {(!isConnected || connectionError) && !isConnecting && (
          <ConnectionCard
            isConnected={isConnected}
            isConnecting={isConnecting}
            connectionType="database"
            lastConnectionTime={lastConnectionTime || undefined}
            error={connectionError || undefined}
            onRetry={handleRetryConnection}
          />
        )}

        {/* Filter Panel */}
        <div className="relative">
          <div className="absolute inset-0 bg-gradient-to-r from-slate-500/5 to-blue-500/5 rounded-2xl" />
          <div className="relative">
            {isConnecting ? (
              <div className="bg-white/80 backdrop-blur-sm border border-white/20 rounded-2xl p-8 shadow-lg">
                <LoadingOverlay type="connection" message="Establishing connection to PostgreSQL database..." />
              </div>
            ) : !isConnected ? (
              <div className="bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl p-8 shadow-lg text-center">
                <div className="space-y-4">
                  <div className="p-4 bg-amber-50 rounded-full w-fit mx-auto">
                    <AlertCircle className="w-8 h-8 text-amber-600" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">Database Connection Required</h3>
                    <p className="text-muted-foreground mt-1">
                      Please establish a database connection to load filter options
                    </p>
                  </div>
                </div>
              </div>
            ) : isLoadingFilters ? (
              <div className="bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl shadow-lg">
                <FilterLoadingSkeleton />
              </div>
            ) : (
              <div className="bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl shadow-lg">
                <FilterPanel
                  filterOptions={filterOptions || {
                    lineOfBusiness: [],
                    commitmentSizeGroup: [],
                    riskGroup: [],
                    bankId: [],
                    region: [],
                    naicsGrpName: []
                  }}
                  selectedFilters={selectedFilters}
                  onFilterChange={handleFilterChange}
                  onCustomRangeAdd={handleCustomRangeAdd}
                  onCustomRangeRemove={handleCustomRangeRemove}
                  onClearFilters={handleClearFilters}
                  onRunQuery={handleRunQuery}
                  disabled={!isConnected}
                />
              </div>
            )}
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-slate-500/5 to-blue-500/5 rounded-2xl" />
            <div className="relative bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl p-8 shadow-lg">
              <LoadingOverlay 
                type="query" 
                message={queryProgress || 'Executing query and processing results...'}
              />
            </div>
          </div>
        )}

        {/* Results */}
        {hasRunQuery && !isLoading && (
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-slate-500/5 to-blue-500/5 rounded-2xl" />
            <div className="relative bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl shadow-lg">
              <Tabs defaultValue="table" className="space-y-6 p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-2 bg-gradient-to-br from-slate-700 to-blue-700 rounded-xl">
                      <BarChart3 className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-lg">Query Results</h3>
                      <p className="text-sm text-muted-foreground">
                        Analysis results for your selected filters
                      </p>
                    </div>
                  </div>
                  <TabsList className="bg-white/70 backdrop-blur-sm border border-slate-200/50">
                    <TabsTrigger value="table" className="flex items-center gap-2 data-[state=active]:bg-white/80">
                      <Table2 className="w-4 h-4" />
                      Table View
                    </TabsTrigger>
                    <TabsTrigger value="charts" className="flex items-center gap-2 data-[state=active]:bg-white/80">
                      <BarChart3 className="w-4 h-4" />
                      Chart View
                    </TabsTrigger>
                  </TabsList>
                </div>

                <div className="flex items-center justify-between bg-gradient-to-r from-slate-50/80 to-blue-50/30 rounded-xl p-4 border border-slate-200/50">
                  <div className="flex items-center gap-6">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                      <span className="text-sm font-medium">Live Data</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {queryResults.length} records • Latest: {getLatestPeriod()}
                    </div>
                  </div>
                  <Badge variant="secondary" className="bg-white/70">
                    Updated {lastDataUpdate?.toLocaleTimeString() || 'Just now'}
                  </Badge>
                </div>

                <TabsContent value="table" className="mt-0">
                  {isLoading ? (
                    <DataLoadingSkeleton />
                  ) : (
                    <div className="bg-white/70 backdrop-blur-sm rounded-xl border border-slate-200/40">
                      <DataTable data={queryResults} />
                    </div>
                  )}
                </TabsContent>

                <TabsContent value="charts" className="mt-0">
                  {isLoading ? (
                    <ChartLoadingSkeleton />
                  ) : (
                    <div className="bg-white/70 backdrop-blur-sm rounded-xl border border-slate-200/40">
                      <ChartVisualization data={queryResults} />
                    </div>
                  )}
                </TabsContent>
              </Tabs>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!hasRunQuery && !isLoading && isConnected && !isLoadingFilters && (
          <div className="relative">
            <div className="absolute inset-0 bg-gradient-to-r from-slate-500/5 to-blue-500/5 rounded-2xl" />
            <div className="relative bg-white/90 backdrop-blur-sm border border-slate-200/50 rounded-2xl p-12 shadow-lg text-center">
              <div className="space-y-6 max-w-md mx-auto">
                <div className="relative">
                  <div className="w-20 h-20 bg-gradient-to-br from-slate-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto">
                    <BarChart3 className="w-10 h-10 text-slate-600" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-6 h-6 bg-green-500 rounded-full flex items-center justify-center">
                    <div className="w-2 h-2 bg-white rounded-full" />
                  </div>
                </div>
                <div className="space-y-2">
                  <h3 className="text-xl font-semibold">Ready to Analyze</h3>
                  <p className="text-muted-foreground">
                    Select filters above and run a query to start analyzing your financial portfolio data
                  </p>
                </div>
                <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground">
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                    <span>Database Connected</span>
                  </div>
                  <div className="flex items-center gap-1">
                    <div className="w-2 h-2 bg-blue-500 rounded-full" />
                    <span>Filters Ready</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}