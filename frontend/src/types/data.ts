export interface DateFilter {
  operator: 'equals' | 'greaterThan' | 'lessThan' | 'between';
  startDate: Date;
  endDate?: Date; // Only used for 'between' operator
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

export interface AnalyticsData {
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

export interface CustomCommitmentRange {
  id: string;
  label: string;
  min: number;
  max: number;
}

export interface SelectedFilters {
  sbaClassification: string[];
  lineOfBusiness: string[];
  commitmentSizeGroup: string[];
  customCommitmentRanges: CustomCommitmentRange[];
  riskGroup: string[];
  bankId: string[];
  region: string[];
  naicsGrpName: string[];
  dateFilters: DateFilter[];
}