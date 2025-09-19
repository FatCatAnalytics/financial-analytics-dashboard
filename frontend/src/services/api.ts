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

// Simple in-flight dedupe map and TTL cache
type CacheEntry<T> = { value: T; expiresAt: number };
const inflight = new Map<string, Promise<any>>();
const cache = new Map<string, CacheEntry<any>>();

function cacheKey(endpoint: string, body?: unknown) {
  return `${endpoint}::${body ? JSON.stringify(body) : ''}`;
}

function getCached<T>(key: string): T | undefined {
  const entry = cache.get(key);
  if (!entry) return undefined;
  if (Date.now() > entry.expiresAt) {
    cache.delete(key);
    return undefined;
  }
  return entry.value as T;
}

function setCached<T>(key: string, value: T, ttlMs: number) {
  cache.set(key, { value, expiresAt: Date.now() + ttlMs });
}

class ApiService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}, cacheTtlMs = 0, dedupeKey?: string): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const key = dedupeKey || cacheKey(endpoint, options.body);

    if (cacheTtlMs > 0) {
      const hit = getCached<T>(key);
      if (hit !== undefined) return hit;
    }

    if (inflight.has(key)) {
      return inflight.get(key) as Promise<T>;
    }

    const p = (async () => {
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
        if (cacheTtlMs > 0) setCached(key, data, cacheTtlMs);
        return data;
      } finally {
        inflight.delete(key);
      }
    })();

    inflight.set(key, p);
    return p;
  }

  // Health check (short cache)
  async healthCheck(): Promise<{ status: string; database: string; timestamp: string }> {
    return this.request('/health', {}, 5_000);
  }

  // Connection status for the frontend dashboard (short cache)
  async getConnectionStatus(): Promise<ConnectionStatus> {
    try {
      return await this.request('/api/connection-status', {}, 5_000);
    } catch (error) {
      return {
        isConnected: false,
        error: error instanceof Error ? error.message : 'Connection failed',
        lastConnectionTime: undefined,
      };
    }
  }

  // Get filter options (longer cache)
  async getFilterOptions(): Promise<FilterOptions> {
    return this.request('/api/filter-options', {}, 60_000);
  }

  // Execute filtered query (no cache, dedupe by body)
  async executeQuery(queryRequest: QueryRequest): Promise<ApiResponse<any[]>> {
    return this.request('/api/query', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    }, 0);
  }

  // Get analytics data (cache by limit)
  async getAnalyticsData(limit?: number): Promise<ApiResponse<AnalyticsRecord[]>> {
    const params = limit ? `?limit=${limit}` : '';
    return this.request(`/api/analytics-data${params}`, {}, 30_000, `/api/analytics-data${params}`);
  }

  // Get summary statistics (cache)
  async getSummaryStats(): Promise<ApiResponse<{ summary: SummaryStats; latestMonth: any }>> {
    return this.request('/api/summary-stats', {}, 30_000);
  }

  // Execute capped vs uncapped analysis (no cache, dedupe by body)
  async executeCappedAnalysis(queryRequest: QueryRequest): Promise<ApiResponse<any[]>> {
    return this.request('/api/execute-capped-analysis', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    }, 0);
  }

  // Simulate the query execution with progress updates (calls capped analysis)
  async simulateQueryExecution(
    queryRequest: QueryRequest,
    onProgress?: (message: string) => void
  ): Promise<AnalyticsRecord[]> {
    const progressMessages = [
      'Initializing capped vs uncapped analysis...',
      'Building SQL query from filters...',
      'Running setup_groups analysis...',
      'Executing testCappedvsUncapped function...',
      'Processing capped vs uncapped results...',
    ];

    for (let i = 0; i < progressMessages.length; i++) {
      if (onProgress) onProgress(progressMessages[i]);
      await new Promise(resolve => setTimeout(resolve, 400 + Math.random() * 600));
    }

    const response = await this.executeCappedAnalysis(queryRequest);
    if (!response.success) {
      throw new Error(response.error || 'Failed to execute capped analysis');
    }

    return response.data;
  }

  // Test the connection (cache short)
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
