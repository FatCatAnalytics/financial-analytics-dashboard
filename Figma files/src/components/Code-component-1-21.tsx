import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from './ui/table';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { AnalyticsData } from '../types/data';

interface DataTableProps {
  data: AnalyticsData[];
}

export function DataTable({ data }: DataTableProps) {
  const formatNumber = (value: number | null) => {
    if (value === null || isNaN(value)) return 'N/A';
    if (Math.abs(value) > 1000000) {
      return (value / 1000000).toFixed(2) + 'M';
    }
    if (Math.abs(value) > 1000) {
      return (value / 1000).toFixed(2) + 'K';
    }
    return value.toFixed(2);
  };

  const formatPercentage = (value: number | null) => {
    if (value === null || isNaN(value)) return 'N/A';
    return (value * 100).toFixed(2) + '%';
  };

  const getDiffBadgeVariant = (value: number | null) => {
    if (value === null || isNaN(value)) return 'secondary';
    return value >= 0 ? 'default' : 'destructive';
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Analytics Results</CardTitle>
        <p className="text-sm text-muted-foreground">
          Showing {data.length} records
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead className="text-right">Commitment Amt</TableHead>
                <TableHead className="text-right">Deals</TableHead>
                <TableHead className="text-right">Outstanding Amt</TableHead>
                <TableHead className="text-right">Prior Date</TableHead>
                <TableHead className="text-right">Prior Commitment</TableHead>
                <TableHead className="text-right">Prior Outstanding</TableHead>
                <TableHead className="text-right">Prior Deals</TableHead>
                <TableHead className="text-center">CA Diff</TableHead>
                <TableHead className="text-center">OA Diff</TableHead>
                <TableHead className="text-center">Deals Diff</TableHead>
                <TableHead className="text-center">CA Model Diff</TableHead>
                <TableHead className="text-center">OA Model Diff</TableHead>
                <TableHead className="text-center">Deals Model Diff</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((row, index) => (
                <TableRow key={index}>
                  <TableCell className="font-medium">
                    {new Date(row.ProcessingDateKey).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(row.CommitmentAmt)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(row.Deals)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(row.OutstandingAmt)}
                  </TableCell>
                  <TableCell className="text-right">
                    {row.ProcessingDateKeyPrior === '0' ? 'N/A' : new Date(row.ProcessingDateKeyPrior).toLocaleDateString()}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(row.CommitmentAmtPrior)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(row.OutstandingAmtPrior)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatNumber(row.DealsPrior)}
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={getDiffBadgeVariant(row.ca_diff)}>
                      {formatPercentage(row.ca_diff)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={getDiffBadgeVariant(row.oa_diff)}>
                      {formatPercentage(row.oa_diff)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={getDiffBadgeVariant(row.deals_diff)}>
                      {formatPercentage(row.deals_diff)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={getDiffBadgeVariant(row.ca_model_diff)}>
                      {formatPercentage(row.ca_model_diff)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={getDiffBadgeVariant(row.oa_model_diff)}>
                      {formatPercentage(row.oa_model_diff)}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-center">
                    <Badge variant={getDiffBadgeVariant(row.deals_model_diff)}>
                      {formatPercentage(row.deals_model_diff)}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </CardContent>
    </Card>
  );
}