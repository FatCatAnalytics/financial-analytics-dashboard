import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { Badge } from './ui/badge';
import { TrendingUp, TrendingDown, Minus, BarChart3, Target, Activity } from 'lucide-react';
import type { AnalyticsData } from '../types/data';

interface ChartVisualizationProps {
  data: AnalyticsData[];
}

// Professional color palette for financial data
const colors = {
  primary: '#1e40af',      // Blue 700 - Primary financial metric
  secondary: '#0891b2',    // Cyan 600 - Secondary financial metric  
  accent: '#059669',       // Emerald 600 - Success/positive
  warning: '#dc2626',      // Red 600 - Negative/risk
  purple: '#7c3aed',       // Violet 600 - Model predictions
  gray: '#64748b',         // Slate 500 - Neutral
  light: '#94a3b8',        // Slate 400 - Grid/subtle elements
};

export function ChartVisualization({ data }: ChartVisualizationProps) {
  const formatNumber = (value: number) => {
    if (Math.abs(value) > 1000000000) {
      return (value / 1000000000).toFixed(1) + 'B';
    }
    if (Math.abs(value) > 1000000) {
      return (value / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(value) > 1000) {
      return (value / 1000).toFixed(1) + 'K';
    }
    return value.toString();
  };


  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatDateFromYYYYMMDD = (dateStr: string) => {
    if (!dateStr || dateStr === '0') return new Date();
    
    // Parse YYYYMMDD format
    if (dateStr.length === 8) {
      const year = dateStr.substring(0, 4);
      const month = dateStr.substring(4, 6);
      const day = dateStr.substring(6, 8);
      return new Date(parseInt(year), parseInt(month) - 1, parseInt(day));
    }
    
    return new Date(dateStr); // fallback
  };

  // Calculate benchmark/indexed values (base 100)
  const calculateBenchmarkData = () => {
    if (data.length === 0) return [];
    
    // Get base values from first observation
    const baseCommitment = data[0].CommitmentAmt;
    const baseOutstanding = data[0].OutstandingAmt;
    const baseDeals = data[0].Deals;
    
    return data.map((row, index) => {
      // Ensure first observation is always 100
      if (index === 0) {
        return {
          commitmentIndex: 100,
          outstandingIndex: 100,
          dealsIndex: 100,
        };
      }
      
      // Calculate relative performance for subsequent observations
      const commitmentIndex = baseCommitment && baseCommitment > 0 
        ? (row.CommitmentAmt / baseCommitment) * 100 
        : 100;
      const outstandingIndex = baseOutstanding && baseOutstanding > 0 
        ? (row.OutstandingAmt / baseOutstanding) * 100 
        : 100;
      const dealsIndex = baseDeals && baseDeals > 0 
        ? (row.Deals / baseDeals) * 100 
        : 100;
      
      return {
        commitmentIndex,
        outstandingIndex,
        dealsIndex,
      };
    });
  };

  const benchmarkData = calculateBenchmarkData();

  const chartData = data.map((row, index) => {
    const parsedDate = formatDateFromYYYYMMDD(row.ProcessingDateKey);
    return {
      date: parsedDate.toLocaleDateString('en-US', { 
        year: '2-digit', 
        month: 'short' 
      }),
      fullDate: parsedDate.toLocaleDateString('en-US', { 
        year: 'numeric', 
        month: 'long' 
      }),
      commitmentAmt: row.CommitmentAmt,
      outstandingAmt: row.OutstandingAmt,
      deals: row.Deals,
      caDiff: row.ca_diff ? row.ca_diff * 100 : null,
      oaDiff: row.oa_diff ? row.oa_diff * 100 : null,
      dealsDiff: row.deals_diff ? row.deals_diff * 100 : null,
      caModelDiff: row.ca_model_diff ? row.ca_model_diff * 100 : null,
      oaModelDiff: row.oa_model_diff ? row.oa_model_diff * 100 : null,
      dealsModelDiff: row.deals_model_diff ? row.deals_model_diff * 100 : null,
      // Add benchmark indices
      commitmentIndex: benchmarkData[index]?.commitmentIndex || 100,
      outstandingIndex: benchmarkData[index]?.outstandingIndex || 100,
      dealsIndex: benchmarkData[index]?.dealsIndex || 100,
    };
  });

  const getMetricSummary = (dataKey: string, label: string) => {
    const values = chartData.map(d => d[dataKey as keyof typeof d]).filter(v => v !== null) as number[];
    const latest = values[values.length - 1];
    const previous = values[values.length - 2];
    const trend = latest > previous ? 'up' : latest < previous ? 'down' : 'stable';
    const change = previous ? ((latest - previous) / previous) * 100 : 0;
    
    return { latest, trend, change, label };
  };

  const commitmentSummary = getMetricSummary('commitmentAmt', 'Commitment Amount');
  const outstandingSummary = getMetricSummary('outstandingAmt', 'Outstanding Amount');
  const dealsSummary = getMetricSummary('deals', 'Deals');

  // Custom tooltip for professional appearance
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-white/95 backdrop-blur-sm border border-slate-200 rounded-xl p-4 shadow-xl">
          <p className="font-medium text-slate-700 mb-2">{`Period: ${label}`}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center gap-2 text-sm">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-slate-600">{entry.dataKey}:</span>
              <span className="font-medium text-slate-900">
                {entry.dataKey.includes('Amount') 
                  ? formatCurrency(entry.value)
                  : entry.dataKey.includes('Index')
                  ? `${entry.value?.toFixed(1)}`
                  : entry.dataKey.includes('Diff') || entry.dataKey.includes('%')
                  ? `${entry.value?.toFixed(2)}%`
                  : formatNumber(entry.value)
                }
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  return (
    <Card className="w-full border-0 bg-transparent shadow-none">
      <CardHeader className="pb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-slate-700 to-blue-700 rounded-xl">
            <Activity className="w-5 h-5 text-white" />
          </div>
          <div>
            <CardTitle className="text-xl">Financial Data Analysis</CardTitle>
            <p className="text-sm text-muted-foreground">
              Comprehensive visualization of portfolio performance and trends
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        <Tabs defaultValue="timeseries" className="space-y-6">
          <TabsList className="grid w-full grid-cols-6 bg-white/70 backdrop-blur-sm border border-slate-200/50">
            <TabsTrigger value="timeseries" className="data-[state=active]:bg-white/90">Time Series</TabsTrigger>
            <TabsTrigger value="benchmark" className="data-[state=active]:bg-white/90">Benchmark</TabsTrigger>
            <TabsTrigger value="individual" className="data-[state=active]:bg-white/90">Individual</TabsTrigger>
            <TabsTrigger value="comparisons" className="data-[state=active]:bg-white/90">Actual vs Model</TabsTrigger>
            <TabsTrigger value="differences" className="data-[state=active]:bg-white/90">Differences</TabsTrigger>
            <TabsTrigger value="overview" className="data-[state=active]:bg-white/90">Overview</TabsTrigger>
          </TabsList>

          {/* Time Series - Combined View */}
          <TabsContent value="timeseries" className="space-y-6">
            {/* Enhanced Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[commitmentSummary, outstandingSummary, dealsSummary].map((summary, index) => (
                <Card key={index} className="relative overflow-hidden bg-gradient-to-br from-white to-slate-50/50 border-slate-200/50 shadow-sm">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            index === 0 ? 'bg-blue-500' : 
                            index === 1 ? 'bg-cyan-500' : 'bg-emerald-500'
                          }`} />
                          <p className="text-sm font-medium text-slate-600">{summary.label}</p>
                        </div>
                        <p className="text-2xl font-bold text-slate-900">
                          {summary.label.includes('Amount') 
                            ? formatCurrency(summary.latest) 
                            : formatNumber(summary.latest)
                          }
                        </p>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        {summary.trend === 'up' && <TrendingUp className="w-5 h-5 text-emerald-600" />}
                        {summary.trend === 'down' && <TrendingDown className="w-5 h-5 text-red-600" />}
                        {summary.trend === 'stable' && <Minus className="w-5 h-5 text-slate-500" />}
                        <Badge variant={
                          summary.change > 0 ? 'default' : 
                          summary.change < 0 ? 'destructive' : 'secondary'
                        } className="text-xs">
                          {summary.change > 0 ? '+' : ''}{summary.change.toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                  <div className={`absolute bottom-0 left-0 right-0 h-1 ${
                    index === 0 ? 'bg-gradient-to-r from-blue-500 to-blue-600' :
                    index === 1 ? 'bg-gradient-to-r from-cyan-500 to-cyan-600' :
                    'bg-gradient-to-r from-emerald-500 to-emerald-600'
                  }`} />
                </Card>
              ))}
            </div>

            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-slate-600" />
                  Portfolio Performance Over Time
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Combined view of key financial metrics and deal volume
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                        tickLine={{ stroke: colors.light }}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis 
                        yAxisId="left" 
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                        tickLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        yAxisId="right" 
                        orientation="right" 
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                        tickLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend 
                        wrapperStyle={{ paddingTop: '20px' }}
                        iconType="circle"
                      />
                      <Line 
                        yAxisId="left"
                        type="monotone" 
                        dataKey="commitmentAmt" 
                        stroke={colors.primary}
                        strokeWidth={3}
                        dot={{ fill: colors.primary, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 6, fill: colors.primary }}
                        name="Commitment Amount"
                      />
                      <Line 
                        yAxisId="left"
                        type="monotone" 
                        dataKey="outstandingAmt" 
                        stroke={colors.secondary}
                        strokeWidth={3}
                        dot={{ fill: colors.secondary, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 6, fill: colors.secondary }}
                        name="Outstanding Amount"
                      />
                      <Line 
                        yAxisId="right"
                        type="monotone" 
                        dataKey="deals" 
                        stroke={colors.accent}
                        strokeWidth={3}
                        dot={{ fill: colors.accent, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 6, fill: colors.accent }}
                        name="Number of Deals"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Benchmark Analysis */}
          <TabsContent value="benchmark" className="space-y-6">
            {/* Benchmark Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {[
                { 
                  label: 'Commitment Performance', 
                  value: chartData[chartData.length - 1]?.commitmentIndex || 100,
                  color: 'blue',
                  metric: 'commitmentIndex'
                },
                { 
                  label: 'Outstanding Performance', 
                  value: chartData[chartData.length - 1]?.outstandingIndex || 100,
                  color: 'cyan',
                  metric: 'outstandingIndex'
                },
                { 
                  label: 'Deal Volume Performance', 
                  value: chartData[chartData.length - 1]?.dealsIndex || 100,
                  color: 'emerald',
                  metric: 'dealsIndex'
                }
              ].map((summary, index) => (
                <Card key={index} className="relative overflow-hidden bg-gradient-to-br from-white to-slate-50/50 border-slate-200/50 shadow-sm">
                  <CardContent className="p-6">
                    <div className="flex items-center justify-between">
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${
                            summary.color === 'blue' ? 'bg-blue-500' : 
                            summary.color === 'cyan' ? 'bg-cyan-500' : 'bg-emerald-500'
                          }`} />
                          <p className="text-sm font-medium text-slate-600">{summary.label}</p>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <p className="text-2xl font-bold text-slate-900">
                            {summary.value.toFixed(1)}
                          </p>
                          <span className="text-sm text-slate-500">vs Base (100)</span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-2">
                        {summary.value > 100 && <TrendingUp className="w-5 h-5 text-emerald-600" />}
                        {summary.value < 100 && <TrendingDown className="w-5 h-5 text-red-600" />}
                        {summary.value === 100 && <Minus className="w-5 h-5 text-slate-500" />}
                        <Badge variant={
                          summary.value > 100 ? 'default' : 
                          summary.value < 100 ? 'destructive' : 'secondary'
                        } className="text-xs">
                          {summary.value > 100 ? '+' : ''}{(summary.value - 100).toFixed(1)}%
                        </Badge>
                      </div>
                    </div>
                  </CardContent>
                  <div className={`absolute bottom-0 left-0 right-0 h-1 ${
                    summary.color === 'blue' ? 'bg-gradient-to-r from-blue-500 to-blue-600' :
                    summary.color === 'cyan' ? 'bg-gradient-to-r from-cyan-500 to-cyan-600' :
                    'bg-gradient-to-r from-emerald-500 to-emerald-600'
                  }`} />
                </Card>
              ))}
            </div>

            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-slate-600" />
                  Benchmark Performance Analysis
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  All metrics indexed to base 100 for relative performance comparison
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                        tickLine={{ stroke: colors.light }}
                        angle={-45}
                        textAnchor="end"
                        height={60}
                      />
                      <YAxis 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                        tickLine={{ stroke: colors.light }}
                        domain={['dataMin - 5', 'dataMax + 5']}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend 
                        wrapperStyle={{ paddingTop: '20px' }}
                        iconType="circle"
                      />
                      <ReferenceLine y={100} stroke={colors.gray} strokeDasharray="5 5" strokeWidth={2} />
                      <Line 
                        type="monotone" 
                        dataKey="commitmentIndex" 
                        stroke={colors.primary}
                        strokeWidth={3}
                        dot={{ fill: colors.primary, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 6, fill: colors.primary }}
                        name="Commitment Amount (Index)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="outstandingIndex" 
                        stroke={colors.secondary}
                        strokeWidth={3}
                        dot={{ fill: colors.secondary, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 6, fill: colors.secondary }}
                        name="Outstanding Amount (Index)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="dealsIndex" 
                        stroke={colors.accent}
                        strokeWidth={3}
                        dot={{ fill: colors.accent, strokeWidth: 2, r: 5 }}
                        activeDot={{ r: 6, fill: colors.accent }}
                        name="Deal Volume (Index)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Individual Benchmark Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    Financial Metrics Benchmark
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Commitment vs Outstanding performance relative to baseline
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="commitmentIndexGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={colors.primary} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={colors.primary} stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="outstandingIndexGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={colors.secondary} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={colors.secondary} stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                        <XAxis 
                          dataKey="date" 
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                        />
                        <YAxis 
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                          domain={['dataMin - 5', 'dataMax + 5']}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconType="circle" />
                        <ReferenceLine y={100} stroke={colors.gray} strokeDasharray="3 3" />
                        <Area
                          type="monotone"
                          dataKey="commitmentIndex"
                          stackId="1"
                          stroke={colors.primary}
                          fill="url(#commitmentIndexGradient)"
                          strokeWidth={2}
                          name="Commitment Index"
                        />
                        <Area
                          type="monotone"
                          dataKey="outstandingIndex"
                          stackId="2"
                          stroke={colors.secondary}
                          fill="url(#outstandingIndexGradient)"
                          strokeWidth={2}
                          name="Outstanding Index"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-emerald-500" />
                    Deal Volume Benchmark
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Transaction volume performance vs baseline period
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <defs>
                          <linearGradient id="dealsIndexGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={colors.accent} stopOpacity={0.8}/>
                            <stop offset="95%" stopColor={colors.accent} stopOpacity={0.4}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                        <XAxis 
                          dataKey="date" 
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                        />
                        <YAxis 
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                          domain={[0, 'dataMax + 10']}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <ReferenceLine y={100} stroke={colors.gray} strokeDasharray="3 3" />
                        <Bar 
                          dataKey="dealsIndex" 
                          fill="url(#dealsIndexGradient)"
                          radius={[6, 6, 0, 0]}
                          stroke={colors.accent}
                          strokeWidth={1}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Benchmark Insights */}
            <Card className="bg-gradient-to-r from-slate-50/80 to-blue-50/30 border-slate-200/50 shadow-sm">
              <CardContent className="p-6">
                <div className="flex items-start gap-3">
                  <div className="p-2 bg-blue-100 rounded-lg">
                    <Target className="w-5 h-5 text-blue-600" />
                  </div>
                  <div className="space-y-2">
                    <h4 className="font-medium text-slate-900">Benchmark Analysis Key</h4>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm text-slate-600">
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-slate-400 rounded-full" />
                        <span><strong>Index 100:</strong> Baseline performance</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-emerald-500 rounded-full" />
                        <span><strong>Above 100:</strong> Outperforming baseline</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <div className="w-2 h-2 bg-red-500 rounded-full" />
                        <span><strong>Below 100:</strong> Underperforming baseline</span>
                      </div>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Individual Metrics */}
          <TabsContent value="individual" className="space-y-6">
            {/* Commitment Amount */}
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  Commitment Amount Over Time
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Total committed capital across all portfolio positions
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="commitmentGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={colors.primary} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={colors.primary} stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="commitmentAmt"
                        stroke={colors.primary}
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#commitmentGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Outstanding Amount */}
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-cyan-500" />
                  Outstanding Amount Over Time
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Current outstanding balances across portfolio
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="outstandingGradient" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor={colors.secondary} stopOpacity={0.3}/>
                          <stop offset="95%" stopColor={colors.secondary} stopOpacity={0.1}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Area
                        type="monotone"
                        dataKey="outstandingAmt"
                        stroke={colors.secondary}
                        strokeWidth={3}
                        fillOpacity={1}
                        fill="url(#outstandingGradient)"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Deals */}
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-emerald-500" />
                  Deal Volume Over Time
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Number of active deals in portfolio by period
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={formatNumber}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Bar 
                        dataKey="deals" 
                        fill={colors.accent}
                        radius={[6, 6, 0, 0]}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Actual vs Model Comparisons */}
          <TabsContent value="comparisons" className="space-y-6">
            {/* CA Diff vs CA Model Diff */}
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-slate-600" />
                  Commitment Amount: Actual vs Model Performance
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Compare actual period-over-period changes with model predictions
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={(value) => value + '%'}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" />
                      <ReferenceLine y={0} stroke={colors.gray} strokeDasharray="3 3" />
                      <Line 
                        type="monotone" 
                        dataKey="caDiff" 
                        stroke={colors.primary}
                        strokeWidth={3}
                        dot={{ fill: colors.primary, strokeWidth: 2, r: 4 }}
                        name="Actual CA Change (%)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="caModelDiff" 
                        stroke={colors.purple}
                        strokeWidth={3}
                        strokeDasharray="8 4"
                        dot={{ fill: colors.purple, strokeWidth: 2, r: 4 }}
                        name="Model CA Prediction (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* OA Diff vs OA Model Diff */}
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-slate-600" />
                  Outstanding Amount: Actual vs Model Performance
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Compare actual period-over-period changes with model predictions
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={(value) => value + '%'}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" />
                      <ReferenceLine y={0} stroke={colors.gray} strokeDasharray="3 3" />
                      <Line 
                        type="monotone" 
                        dataKey="oaDiff" 
                        stroke={colors.secondary}
                        strokeWidth={3}
                        dot={{ fill: colors.secondary, strokeWidth: 2, r: 4 }}
                        name="Actual OA Change (%)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="oaModelDiff" 
                        stroke={colors.purple}
                        strokeWidth={3}
                        strokeDasharray="8 4"
                        dot={{ fill: colors.purple, strokeWidth: 2, r: 4 }}
                        name="Model OA Prediction (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>

            {/* Deals Diff vs Deals Model Diff */}
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Target className="w-5 h-5 text-slate-600" />
                  Deal Volume: Actual vs Model Performance
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Compare actual period-over-period changes with model predictions
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={(value) => value + '%'}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" />
                      <ReferenceLine y={0} stroke={colors.gray} strokeDasharray="3 3" />
                      <Line 
                        type="monotone" 
                        dataKey="dealsDiff" 
                        stroke={colors.accent}
                        strokeWidth={3}
                        dot={{ fill: colors.accent, strokeWidth: 2, r: 4 }}
                        name="Actual Deals Change (%)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="dealsModelDiff" 
                        stroke={colors.purple}
                        strokeWidth={3}
                        strokeDasharray="8 4"
                        dot={{ fill: colors.purple, strokeWidth: 2, r: 4 }}
                        name="Model Deals Prediction (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* All Differences */}
          <TabsContent value="differences" className="space-y-6">
            <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="w-5 h-5 text-slate-600" />
                  Period-over-Period Performance Changes
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  Comparative view of all metrics' percentage changes over time
                </p>
              </CardHeader>
              <CardContent>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData}>
                      <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                      <XAxis 
                        dataKey="date" 
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <YAxis 
                        tickFormatter={(value) => value + '%'}
                        tick={{ fontSize: 12, fill: colors.gray }}
                        axisLine={{ stroke: colors.light }}
                      />
                      <Tooltip content={<CustomTooltip />} />
                      <Legend iconType="circle" />
                      <ReferenceLine y={0} stroke={colors.gray} strokeDasharray="3 3" />
                      <Line 
                        type="monotone" 
                        dataKey="caDiff" 
                        stroke={colors.primary}
                        strokeWidth={3}
                        dot={{ fill: colors.primary, strokeWidth: 2, r: 4 }}
                        name="Commitment Amount Change (%)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="oaDiff" 
                        stroke={colors.secondary}
                        strokeWidth={3}
                        dot={{ fill: colors.secondary, strokeWidth: 2, r: 4 }}
                        name="Outstanding Amount Change (%)"
                      />
                      <Line 
                        type="monotone" 
                        dataKey="dealsDiff" 
                        stroke={colors.accent}
                        strokeWidth={3}
                        dot={{ fill: colors.accent, strokeWidth: 2, r: 4 }}
                        name="Deal Volume Change (%)"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Overview */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-blue-500" />
                    Financial Portfolio Trends
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Commitment vs Outstanding amounts comparison
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={chartData}>
                        <defs>
                          <linearGradient id="commitmentArea" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={colors.primary} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={colors.primary} stopOpacity={0.1}/>
                          </linearGradient>
                          <linearGradient id="outstandingArea" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={colors.secondary} stopOpacity={0.3}/>
                            <stop offset="95%" stopColor={colors.secondary} stopOpacity={0.1}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                        <XAxis 
                          dataKey="date" 
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                        />
                        <YAxis 
                          tickFormatter={formatNumber}
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Legend iconType="circle" />
                        <Area
                          type="monotone"
                          dataKey="commitmentAmt"
                          stackId="1"
                          stroke={colors.primary}
                          fill="url(#commitmentArea)"
                          strokeWidth={2}
                          name="Commitment"
                        />
                        <Area
                          type="monotone"
                          dataKey="outstandingAmt"
                          stackId="1"
                          stroke={colors.secondary}
                          fill="url(#outstandingArea)"
                          strokeWidth={2}
                          name="Outstanding"
                        />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>

              <Card className="bg-white/80 backdrop-blur-sm border-slate-200/50 shadow-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-emerald-500" />
                    Deal Activity Volume
                  </CardTitle>
                  <p className="text-sm text-muted-foreground">
                    Transaction frequency and volume patterns
                  </p>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={chartData}>
                        <defs>
                          <linearGradient id="dealGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor={colors.accent} stopOpacity={0.8}/>
                            <stop offset="95%" stopColor={colors.accent} stopOpacity={0.4}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke={colors.light} opacity={0.3} />
                        <XAxis 
                          dataKey="date" 
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                        />
                        <YAxis 
                          tickFormatter={formatNumber}
                          tick={{ fontSize: 12, fill: colors.gray }}
                          axisLine={{ stroke: colors.light }}
                        />
                        <Tooltip content={<CustomTooltip />} />
                        <Bar 
                          dataKey="deals" 
                          fill="url(#dealGradient)"
                          radius={[6, 6, 0, 0]}
                          stroke={colors.accent}
                          strokeWidth={1}
                        />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}