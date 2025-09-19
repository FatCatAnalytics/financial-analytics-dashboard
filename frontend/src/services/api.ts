/**
 * API service for connecting to the backend
 */

const API_BASE_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  totalRecords?: number;
  error?: string;
}

export interface ConnectionStatus {
  isConnected: boolean;
  error?: string;
  lastConnectionTime?: string;
  recordCount?: number;
  maxDate?: string;
}

export interface FilterOptions {
  sbaClassification: string[];
  lineOfBusiness: string[];
  commitmentSizeGroup: string[];
  riskGroup: string[];
  bankId: string[];
  region: string[];
  naicsGrpName: string[];
}

export interface QueryFilters {
  sbaClassification: string[];
  lineOfBusiness: string[];
  commitmentSizeGroup: string[];
  customCommitmentRanges: Array<{
    id: string;
    label: string;
    min: number;
    max: number;
  }>;
  riskGroup: string[];
  bankId: string[];
  region: string[];
  naicsGrpName: string[];
  dateFilters: Array<{
    operator: 'equals' | 'greaterThan' | 'lessThan' | 'between';
    startDate: string; // ISO date string
    endDate?: string; // ISO date string, only for 'between' operator
  }>;
}

export interface QueryRequest {
  filters: QueryFilters;
  limit?: number;
}

export interface AnalyticsRecord {
  ProcessingDateKey: string;
  CommitmentAmt: number;
  Deals: number;
  OutstandingAmt: number;
  ProcessingDateKeyPrior: string;
  CommitmentAmtPrior: number;
  OutstandingAmtPrior: number;
  DealsPrior: number;
  ca_diff: number | null;
  oa_diff: number | null;
  deals_diff: number | null;
  ca_model_diff: number | null;
  oa_model_diff: number | null;
  deals_model_diff: number | null;
}

export interface SummaryStats {
  totalRecords: number;
  uniqueMonths: number;
  dateRange: {
    earliest: string;
    latest: string;
  };
  totals: {
    commitment: number;
    averageCommitment: number;
  };
  uniqueCounts: {
    regions: number;
    lineOfBusiness: number;
    banks: number;
  };
}

class ApiService {
  private baseUrl: string;
  private inflightRequests: Map<string, Promise<any>>;
  private cache: Map<string, { data: any; expiry: number }>;

  constructor() {
    this.baseUrl = API_BASE_URL;
    this.inflightRequests = new Map();
    this.cache = new Map();
  }

  private getCacheKey(endpoint: string, options?: RequestInit) {
    // Cache key includes URL and body (for POST requests)
    const body = options?.body ? `:${typeof options.body === 'string' ? options.body : JSON.stringify(options.body)}` : '';
    return `${endpoint}${body}`;
  }

  private getFromCache<T>(key: string): T | null {
    const entry = this.cache.get(key);
    if (!entry) return null;
    if (Date.now() > entry.expiry) {
      this.cache.delete(key);
      return null;
    }
    return entry.data as T;
  }

  private setCache<T>(key: string, data: T, ttlMs: number) {
    this.cache.set(key, { data, expiry: Date.now() + ttlMs });
  }

  private async request<T>(endpoint: string, options: RequestInit = {}, opts?: { cacheTtlMs?: number }): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const key = this.getCacheKey(endpoint, options);

    // Serve from cache if available
    if (opts?.cacheTtlMs) {
      const cached = this.getFromCache<T>(key);
      if (cached) return cached;
    }

    // Deduplicate inflight requests
    if (this.inflightRequests.has(key)) {
      return this.inflightRequests.get(key)!;
    }

    const fetchPromise = (async () => {
      try {
        const response = await fetch(url, {
          headers: {
            'Content-Type': 'application/json',
            ...options.headers,
          },
          ...options,
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(`HTTP ${response.status}: ${errorText}`);
        }

        const data = (await response.json()) as T;

        // Store in cache if requested
        if (opts?.cacheTtlMs) {
          this.setCache<T>(key, data, opts.cacheTtlMs);
        }

        return data;
      } finally {
        // Always clear inflight entry
        this.inflightRequests.delete(key);
      }
    })();

    this.inflightRequests.set(key, fetchPromise);
    return fetchPromise;
  }

  // Health check
  async healthCheck(): Promise<{ status: string; database: string; timestamp: string }> {
    return this.request('/health');
  }

  // Connection status for the frontend dashboard
  async getConnectionStatus(): Promise<ConnectionStatus> {
    try {
      // Short cache to avoid duplicate calls during quick re-mounts
      return await this.request('/api/connection-status', {}, { cacheTtlMs: 10_000 });
    } catch (error) {
      return {
        isConnected: false,
        error: error instanceof Error ? error.message : 'Connection failed',
        lastConnectionTime: undefined,
      };
    }
  }

  // Get filter options
  async getFilterOptions(): Promise<FilterOptions> {
    // Cache filter options for 5 minutes (backend also caches)
    return this.request('/api/filter-options', {}, { cacheTtlMs: 5 * 60_000 });
  }

  // Execute filtered query
  async executeQuery(queryRequest: QueryRequest): Promise<ApiResponse<any[]>> {
    // Deduplicate identical concurrent query requests
    return this.request('/api/query', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    });
  }

  // Get analytics data (time series)
  async getAnalyticsData(limit?: number): Promise<ApiResponse<AnalyticsRecord[]>> {
    const params = limit ? `?limit=${limit}` : '';
    // Cache time-series briefly to avoid refetch on quick tab switches
    return this.request(`/api/analytics-data${params}`, {}, { cacheTtlMs: 30_000 });
  }

  // Get summary statistics
  async getSummaryStats(): Promise<ApiResponse<{ summary: SummaryStats; latestMonth: any }>> {
    // Cache summary for 60 seconds (backend also caches)
    return this.request('/api/summary-stats', {}, { cacheTtlMs: 60_000 });
  }

  // Execute capped vs uncapped analysis
  // Deprecated on backend; keep method for compatibility (not used)
  async executeCappedAnalysis(_queryRequest: QueryRequest): Promise<ApiResponse<any[]>> {
    throw new Error('executeCappedAnalysis is deprecated. Use executeQuery instead.');
  }

  // Execute query with progress updates and client-side aggregation to avoid duplicate backend work
  async simulateQueryExecution(
    queryRequest: QueryRequest,
    onProgress?: (message: string) => void
  ): Promise<AnalyticsRecord[]> {
    const progressMessages = [
      'Building SQL from filters...',
      'Querying database...',
      'Aggregating results by month...',
      'Calculating prior-period diffs...'
    ];

    for (let i = 0; i < progressMessages.length; i++) {
      if (onProgress) onProgress(progressMessages[i]);
      await new Promise(resolve => setTimeout(resolve, 150));
    }

    const response = await this.executeQuery(queryRequest);
    if (!response.success) {
      throw new Error(response.error || 'Query failed');
    }

    const rows = response.data as Array<any>;

    // Aggregate by ProcessingDateKey (sum amounts, count deals)
    const aggMap = new Map<string, { CommitmentAmt: number; OutstandingAmt: number; Deals: number }>();

    for (const row of rows) {
      // Support both camel and snake case from backend
      const key = String(row.ProcessingDateKey ?? row.processingdatekey);
      const ca = Number(row.CommitmentAmt ?? row.commitmentamt ?? 0);
      const oa = Number(row.OutstandingAmt ?? row.outstandingamt ?? 0);
      const current = aggMap.get(key) || { CommitmentAmt: 0, OutstandingAmt: 0, Deals: 0 };
      current.CommitmentAmt += isFinite(ca) ? ca : 0;
      current.OutstandingAmt += isFinite(oa) ? oa : 0;
      current.Deals += 1;
      aggMap.set(key, current);
    }

    // Sort by date ascending
    const dates = Array.from(aggMap.keys()).sort();

    const records: AnalyticsRecord[] = [];
    let prev: { key: string; CommitmentAmt: number; OutstandingAmt: number; Deals: number } | null = null;

    for (const key of dates) {
      const cur = aggMap.get(key)!;
      const rec: AnalyticsRecord = {
        ProcessingDateKey: key,
        CommitmentAmt: cur.CommitmentAmt,
        Deals: cur.Deals,
        OutstandingAmt: cur.OutstandingAmt,
        ProcessingDateKeyPrior: prev ? prev.key : '0',
        CommitmentAmtPrior: prev ? prev.CommitmentAmt : 0,
        OutstandingAmtPrior: prev ? prev.OutstandingAmt : 0,
        DealsPrior: prev ? prev.Deals : 0,
        ca_diff: prev && prev.CommitmentAmt > 0 ? (cur.CommitmentAmt - prev.CommitmentAmt) / prev.CommitmentAmt : null,
        oa_diff: prev && prev.OutstandingAmt > 0 ? (cur.OutstandingAmt - prev.OutstandingAmt) / prev.OutstandingAmt : null,
        deals_diff: prev && prev.Deals > 0 ? (cur.Deals - prev.Deals) / prev.Deals : null,
        ca_model_diff: null,
        oa_model_diff: null,
        deals_model_diff: null,
      };
      records.push(rec);
      prev = { key, ...cur };
    }

    return records;
  }

  // Test the connection
  async testConnection(): Promise<boolean> {
    try {
      const status = await this.getConnectionStatus();
      return status.isConnected;
    } catch (error) {
      console.error('Connection test failed:', error);
      return false;
    }
  }
}

// Export singleton instance
export const apiService = new ApiService();

// Export individual functions for convenience
export const {
  healthCheck,
  getConnectionStatus,
  getFilterOptions,
  executeQuery,
  executeCappedAnalysis,
  getAnalyticsData,
  getSummaryStats,
  simulateQueryExecution,
  testConnection,
} = apiService;
