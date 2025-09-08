import React from 'react';
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
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './ui/tabs';
import { AnalyticsData } from '../types/data';

interface ChartVisualizationProps {
  data: AnalyticsData[];
}

export function ChartVisualization({ data }: ChartVisualizationProps) {
  const formatNumber = (value: number) => {
    if (Math.abs(value) > 1000000) {
      return (value / 1000000).toFixed(1) + 'M';
    }
    if (Math.abs(value) > 1000) {
      return (value / 1000).toFixed(1) + 'K';
    }
    return value.toString();
  };

  const formatPercentage = (value: number) => {
    return (value * 100).toFixed(2) + '%';
  };

  const chartData = data.map(row => ({
    date: new Date(row.ProcessingDateKey).toLocaleDateString('en-US', { 
      year: '2-digit', 
      month: 'short' 
    }),
    commitmentAmt: row.CommitmentAmt,
    outstandingAmt: row.OutstandingAmt,
    deals: row.Deals,
    caDiff: row.ca_diff ? row.ca_diff * 100 : null,
    oaDiff: row.oa_diff ? row.oa_diff * 100 : null,
    dealsDiff: row.deals_diff ? row.deals_diff * 100 : null,
  }));

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Data Visualization</CardTitle>
      </CardHeader>
      <CardContent>
        <Tabs defaultValue="amounts" className="space-y-4">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="amounts">Amounts</TabsTrigger>
            <TabsTrigger value="deals">Deals</TabsTrigger>
            <TabsTrigger value="trends">Trends</TabsTrigger>
            <TabsTrigger value="differences">Differences</TabsTrigger>
          </TabsList>

          <TabsContent value="amounts" className="space-y-4">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis tickFormatter={formatNumber} />
                  <Tooltip formatter={(value) => formatNumber(Number(value))} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="commitmentAmt" 
                    stroke="hsl(var(--chart-1))" 
                    strokeWidth={2}
                    name="Commitment Amount"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="outstandingAmt" 
                    stroke="hsl(var(--chart-2))" 
                    strokeWidth={2}
                    name="Outstanding Amount"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="deals" className="space-y-4">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis tickFormatter={formatNumber} />
                  <Tooltip formatter={(value) => formatNumber(Number(value))} />
                  <Legend />
                  <Bar 
                    dataKey="deals" 
                    fill="hsl(var(--chart-3))"
                    name="Number of Deals"
                  />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="trends" className="space-y-4">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="commitmentAmt" 
                    stroke="hsl(var(--chart-1))" 
                    strokeWidth={2}
                    name="Commitment Amount"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="outstandingAmt" 
                    stroke="hsl(var(--chart-2))" 
                    strokeWidth={2}
                    name="Outstanding Amount"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="deals" 
                    stroke="hsl(var(--chart-3))" 
                    strokeWidth={2}
                    name="Deals"
                    yAxisId="right"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>

          <TabsContent value="differences" className="space-y-4">
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis tickFormatter={(value) => value + '%'} />
                  <Tooltip formatter={(value) => value ? value.toFixed(2) + '%' : 'N/A'} />
                  <Legend />
                  <Line 
                    type="monotone" 
                    dataKey="caDiff" 
                    stroke="hsl(var(--chart-4))" 
                    strokeWidth={2}
                    name="CA Difference (%)"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="oaDiff" 
                    stroke="hsl(var(--chart-5))" 
                    strokeWidth={2}
                    name="OA Difference (%)"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="dealsDiff" 
                    stroke="hsl(var(--chart-1))" 
                    strokeWidth={2}
                    name="Deals Difference (%)"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  );
}