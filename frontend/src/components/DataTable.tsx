"use client";

import React from "react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

interface AnalyticsData {
	ProcessingDateKey: string | number;
	CommitmentAmt: number;
	Deals: number;
	OutstandingAmt: number;
	ProcessingDateKeyPrior: string | number;
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

interface DataTableProps { data: AnalyticsData[] }

export function DataTable({ data }: DataTableProps) {
	const formatNumber = (value: number | null) => {
		if (value === null || isNaN(value)) return "N/A";
		if (Math.abs(value) > 1000000) return (value / 1000000).toFixed(2) + "M";
		if (Math.abs(value) > 1000) return (value / 1000).toFixed(2) + "K";
		return value.toFixed(2);
	};
	const formatPercentage = (value: number | null) => (value === null || isNaN(value) ? "N/A" : (value * 100).toFixed(2) + "%");
	const badgeVariant = (value: number | null) => (value === null || isNaN(value) ? "secondary" : value >= 0 ? "default" : "destructive");

	return (
		<Card className="w-full">
			<CardHeader>
				<CardTitle>Analytics Results</CardTitle>
				<p className="text-sm text-muted-foreground">Showing {data.length} records</p>
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
							{data.map((row, i) => (
								<TableRow key={i}>
									<TableCell className="font-medium">{new Date(row.ProcessingDateKey).toLocaleDateString()}</TableCell>
									<TableCell className="text-right">{formatNumber(row.CommitmentAmt)}</TableCell>
									<TableCell className="text-right">{formatNumber(row.Deals)}</TableCell>
									<TableCell className="text-right">{formatNumber(row.OutstandingAmt)}</TableCell>
									<TableCell className="text-right">{row.ProcessingDateKeyPrior === "0" ? "N/A" : new Date(row.ProcessingDateKeyPrior).toLocaleDateString()}</TableCell>
									<TableCell className="text-right">{formatNumber(row.CommitmentAmtPrior)}</TableCell>
									<TableCell className="text-right">{formatNumber(row.OutstandingAmtPrior)}</TableCell>
									<TableCell className="text-right">{formatNumber(row.DealsPrior)}</TableCell>
									<TableCell className="text-center"><Badge variant={badgeVariant(row.ca_diff)}>{formatPercentage(row.ca_diff)}</Badge></TableCell>
									<TableCell className="text-center"><Badge variant={badgeVariant(row.oa_diff)}>{formatPercentage(row.oa_diff)}</Badge></TableCell>
									<TableCell className="text-center"><Badge variant={badgeVariant(row.deals_diff)}>{formatPercentage(row.deals_diff)}</Badge></TableCell>
									<TableCell className="text-center"><Badge variant={badgeVariant(row.ca_model_diff)}>{formatPercentage(row.ca_model_diff)}</Badge></TableCell>
									<TableCell className="text-center"><Badge variant={badgeVariant(row.oa_model_diff)}>{formatPercentage(row.oa_model_diff)}</Badge></TableCell>
									<TableCell className="text-center"><Badge variant={badgeVariant(row.deals_model_diff)}>{formatPercentage(row.deals_model_diff)}</Badge></TableCell>
								</TableRow>
							))}
						</TableBody>
					</Table>
				</div>
			</CardContent>
		</Card>
	);
}
