import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Table2, BarChart3, Filter, RefreshCw } from 'lucide-react';
import { FilterPanel } from './components/FilterPanel';
import { DataTable } from './components/DataTable';
import { ChartVisualization } from './components/ChartVisualization';
import { ConnectionStatus, ConnectionCard } from './components/ConnectionStatus';
import { LoadingOverlay, FilterLoadingSkeleton, DataLoadingSkeleton, ChartLoadingSkeleton } from './components/LoadingOverlay';
import { StatusDashboard } from './components/StatusDashboard';
import { mockFilterOptions, mockAnalyticsData } from './data/mockData';
import { SelectedFilters, AnalyticsData, CustomCommitmentRange } from './types/data';

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

  // Simulate database connection on mount
  useEffect(() => {
    const connectToDatabase = async () => {
      setIsConnecting(true);
      
      try {
        // Simulate connection delay
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Simulate occasional connection failures (10% chance)
        if (Math.random() < 0.1) {
          throw new Error('Connection timeout - Unable to reach PostgreSQL database');
        }
        
        setIsConnected(true);
        setConnectionError(null);
        setLastConnectionTime(new Date());
        
        // Load filter options after successful connection
        await loadFilterOptions();
        
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
      // Simulate loading filter options from database
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      // Filter options are loaded (using mock data)
      setIsLoadingFilters(false);
    } catch (error) {
      setIsLoadingFilters(false);
      console.error('Failed to load filter options:', error);
    }
  };

  const handleRetryConnection = async () => {
    setConnectionError(null);
    setIsConnecting(true);
    
    try {
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      if (Math.random() < 0.2) {
        throw new Error('Connection timeout - Unable to reach PostgreSQL database');
      }
      
      setIsConnected(true);
      setLastConnectionTime(new Date());
      await loadFilterOptions();
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
    setQueryProgress('Initializing query...');
    
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setQueryProgress('Building SQL query from filters...');
      
      await new Promise(resolve => setTimeout(resolve, 800));
      setQueryProgress('Executing query against PostgreSQL...');
      
      await new Promise(resolve => setTimeout(resolve, 1200));
      setQueryProgress('Processing results...');
      
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // In a real application, this would filter the data based on selected filters
      // For now, we'll return the mock data
      setQueryResults(mockAnalyticsData);
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

  // Get latest period from data
  const getLatestPeriod = () => {
    if (queryResults.length === 0) return 'Aug 2024';
    const latest = queryResults[queryResults.length - 1];
    const date = new Date(latest.ProcessingDateKey);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
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
                  filterOptions={mockFilterOptions}
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