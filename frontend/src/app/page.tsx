"use client";

import React, { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table2, BarChart3, Filter, RefreshCw, AlertCircle } from 'lucide-react';
import { FilterPanel } from '@/components/FilterPanel';
import { DataTable } from '@/components/DataTable';
import { ChartVisualization } from '@/components/ChartVisualization';
import { ConnectionStatus, ConnectionCard } from '@/components/ConnectionStatus';
import { LoadingOverlay, FilterLoadingSkeleton, DataLoadingSkeleton, ChartLoadingSkeleton } from '@/components/LoadingOverlay';
import { StatusDashboard } from '@/components/StatusDashboard';
import { api } from '@/lib/api';
import { SelectedFilters, AnalyticsData, CustomCommitmentRange } from '@/types/data';

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
  const [filterOptions, setFilterOptions] = useState<any>({});
  const [dataSummary, setDataSummary] = useState<any>({});

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

  // Test real database connection on mount
  useEffect(() => {
    const connectToDatabase = async () => {
      setIsConnecting(true);
      setConnectionError(null);
      
      try {
        console.log("Testing PostgreSQL database connection...");
        
        // Test real database connection
        const dbStatus = await api.dbStatus();
        console.log("Database status:", dbStatus);
        
        if (dbStatus.status === "connected") {
          setIsConnected(true);
          setConnectionError(null);
          setLastConnectionTime(new Date());
          console.log("PostgreSQL database connected successfully");
          
          // Load filter options from database
          await loadFilterOptions();
        } else {
          throw new Error(dbStatus.error || 'Database connection failed');
        }
        
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Connection failed';
        console.error("Database connection failed:", errorMessage);
        setConnectionError(errorMessage);
        setIsConnected(false);
        
        // Still try to load filter options (will use CSV fallback)
        await loadFilterOptions();
      } finally {
        setIsConnecting(false);
      }
    };

    connectToDatabase();
  }, []);

  const loadFilterOptions = async () => {
    setIsLoadingFilters(true);
    
    try {
      // Try to load filter options from PostgreSQL database first
      console.log("Loading filter options from PostgreSQL database...");
      const filters = await api.filters(true); // Use database (true = try database first)
      setFilterOptions(filters);
      console.log("Filter options loaded successfully:", Object.keys(filters));
      setIsLoadingFilters(false);
    } catch (error) {
      console.error('Failed to load filter options:', error);
      setIsLoadingFilters(false);
      // Filters will be empty, but dashboard will still work with CSV fallback
    }
  };

  const handleRetryConnection = async () => {
    setConnectionError(null);
    setIsConnecting(true);
    
    try {
      console.log("Retrying PostgreSQL database connection...");
      
      // Test real database connection
      const dbStatus = await api.dbStatus();
      console.log("Retry database status:", dbStatus);
      
      if (dbStatus.status === "connected") {
        setIsConnected(true);
        setConnectionError(null);
        setLastConnectionTime(new Date());
        console.log("PostgreSQL database reconnected successfully");
        
        // Reload filter options from database
        await loadFilterOptions();
      } else {
        throw new Error(dbStatus.error || 'Database connection failed on retry');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Connection failed';
      console.error("Database retry failed:", errorMessage);
      setConnectionError(errorMessage);
      setIsConnected(false);
    } finally {
      setIsConnecting(false);
    }
  };

  const handleRunQuery = async () => {
    setIsLoading(true);
    setQueryProgress('Initializing query...');
    
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      setQueryProgress('Building SQL query from filters...');
      
      await new Promise(resolve => setTimeout(resolve, 800));
      setQueryProgress('Executing query against PostgreSQL database...');
      
      // Run capped vs uncapped analysis with filters
      const analysisResult = await api.cappedAnalysis({
        selected_columns: [
          "ProcessingDateKey",
          "CommitmentAmt",
          "OutstandingAmt",
          "Deals",
          "ProcessingDateKeyPrior",
          "CommitmentAmtPrior",
          "OutstandingAmtPrior",
          "DealsPrior",
        ],
        region: selectedFilters.region[0] || "Rocky Mountain",
        sba_filter: "Non-SBA",
        line_of_business_ids: selectedFilters.lineOfBusiness.length > 0 ? selectedFilters.lineOfBusiness : undefined,
        commitment_size_groups: selectedFilters.commitmentSizeGroup.length > 0 ? selectedFilters.commitmentSizeGroup : undefined,
        risk_group_descriptions: selectedFilters.riskGroup.length > 0 ? selectedFilters.riskGroup : undefined,
        cap_value: 0.1, // 10% cap
        output_file: `dashboard_analysis_${Date.now()}.csv`
      });
      
      if (analysisResult.error) {
        throw new Error(analysisResult.error);
      }
      
      // Use the capped analysis results as the main data
      const result = {
        rows: analysisResult.analysis_results,
        source: analysisResult.source,
        summary: {
          total_commitment: analysisResult.analysis_results.reduce((sum: number, row: any) => sum + (row.CommitmentAmt || 0), 0),
          total_outstanding: analysisResult.analysis_results.reduce((sum: number, row: any) => sum + (row.OutstandingAmt || 0), 0),
          record_count: analysisResult.record_count,
          latest_period: (analysisResult.analysis_results[analysisResult.analysis_results.length - 1] as any)?.ProcessingDateKey
        }
      };
      
      setQueryProgress('Processing results...');
      await new Promise(resolve => setTimeout(resolve, 500));
      
      console.log("Capped analysis result source:", result.source);
      if (result.source === "database") {
        console.log("Capped analysis successfully completed using PostgreSQL database");
      } else {
        console.log("Capped analysis completed using CSV fallback data");
      }
      
      setQueryResults(result.rows as AnalyticsData[]);
      setDataSummary({
        ...result.summary,
        analysis_type: "capped_vs_uncapped",
        cap_value: 0.1,
        output_file: analysisResult.output_file
      });
      setHasRunQuery(true);
      setQueryProgress('');
      setLastDataUpdate(new Date());
      
    } catch (error) {
      console.error('Query failed:', error);
      setQueryProgress(`Query failed: ${error instanceof Error ? error.message : 'Unknown error'}. Please check database connection.`);
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
    if (dataSummary.latest_period) {
      const date = new Date(dataSummary.latest_period);
      return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    }
    if (queryResults.length === 0) return 'Apr 2023';
    const latest = queryResults[queryResults.length - 1];
    const date = new Date(latest.ProcessingDateKey);
    return date.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
  };

  // Calculate total commitment from latest data
  const getTotalCommitment = () => {
    if (dataSummary.total_commitment) {
      return dataSummary.total_commitment;
    }
    if (queryResults.length === 0) return 2312644807; // From CSV summary
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
          recordCount={dataSummary.record_count || queryResults.length}
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
                  filterOptions={filterOptions}
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
                      <span className="text-sm font-medium">Capped Analysis Data</span>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      {queryResults.length} records • Latest: {getLatestPeriod()} • Cap: {dataSummary.cap_value ? (dataSummary.cap_value * 100).toFixed(0) + '%' : '10%'}
                    </div>
                    {dataSummary.output_file && (
                      <Badge variant="outline" className="text-xs bg-white/70">
                        CSV: {dataSummary.output_file.split('/').pop()}
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge variant="default" className="bg-gradient-to-r from-emerald-600 to-green-600 text-white">
                      testCappedvsUncapped
                    </Badge>
                    <Badge variant="secondary" className="bg-white/70">
                      Updated {lastDataUpdate?.toLocaleTimeString() || 'Just now'}
                    </Badge>
                  </div>
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