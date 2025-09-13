/**
 * API service for connecting to the backend
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
  lineOfBusiness: string[];
  commitmentSizeGroup: string[];
  riskGroup: string[];
  bankId: string[];
  region: string[];
  naicsGrpName: string[];
}

export interface QueryFilters {
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

  constructor() {
    this.baseUrl = API_BASE_URL;
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
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

      const data = await response.json();
      return data;
    } catch (error) {
      console.error(`API request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // Health check
  async healthCheck(): Promise<{ status: string; database: string; timestamp: string }> {
    return this.request('/health');
  }

  // Connection status for the frontend dashboard
  async getConnectionStatus(): Promise<ConnectionStatus> {
    try {
      return await this.request('/api/connection-status');
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
    return this.request('/api/filter-options');
  }

  // Execute filtered query
  async executeQuery(queryRequest: QueryRequest): Promise<ApiResponse<any[]>> {
    return this.request('/api/query', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    });
  }

  // Get analytics data (time series)
  async getAnalyticsData(limit?: number): Promise<ApiResponse<AnalyticsRecord[]>> {
    const params = limit ? `?limit=${limit}` : '';
    return this.request(`/api/analytics-data${params}`);
  }

  // Get summary statistics
  async getSummaryStats(): Promise<ApiResponse<{ summary: SummaryStats; latestMonth: any }>> {
    return this.request('/api/summary-stats');
  }

  // Execute capped vs uncapped analysis
  async executeCappedAnalysis(queryRequest: QueryRequest): Promise<ApiResponse<any[]>> {
    return this.request('/api/execute-capped-analysis', {
      method: 'POST',
      body: JSON.stringify(queryRequest),
    });
  }

  // Simulate the query execution with progress updates (now calls capped analysis)
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
      if (onProgress) {
        onProgress(progressMessages[i]);
      }
      // Simulate processing time
      await new Promise(resolve => setTimeout(resolve, 400 + Math.random() * 600));
    }

    // Execute the actual capped vs uncapped analysis
    const response = await this.executeCappedAnalysis(queryRequest);
    if (!response.success) {
      throw new Error(response.error || 'Failed to execute capped analysis');
    }

    return response.data;
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
