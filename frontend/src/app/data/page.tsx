"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { DataTable } from "@/components/DataTable";
import { AnalyticsData } from "@/types/data";
import { Badge } from "@/components/ui/badge";

export default function DataPage() {
	const [data, setData] = useState<AnalyticsData[]>([]);
	const [err, setErr] = useState<string>("");

	const load = async () => {
		setErr("");
		try {
			// Use capped analysis instead of regular data for more comprehensive results
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
				region: "Rocky Mountain",
				sba_filter: "Non-SBA",
				cap_value: 0.1, // 10% cap
				output_file: `data_page_analysis_${Date.now()}.csv`
			});
			
			if (analysisResult.error) {
				throw new Error(analysisResult.error);
			}
			
			const res = {
				rows: analysisResult.analysis_results,
				source: analysisResult.source
			};
			
			// Transform capped analysis results to match DataTable format
			const transformedData = res.rows.map((row: any) => {
				// Convert ProcessingDateKey from integer format (YYYYMMDD) to date string
				const dateStr = row.ProcessingDateKey ? row.ProcessingDateKey.toString() : '0';
				const formattedDate = dateStr.length === 8 ? 
					`${dateStr.slice(0,4)}-${dateStr.slice(4,6)}-${dateStr.slice(6,8)}` : 
					dateStr;
				
				const priorDateStr = row.ProcessingDateKeyPrior ? row.ProcessingDateKeyPrior.toString() : '0';
				const formattedPriorDate = priorDateStr.length === 8 ? 
					`${priorDateStr.slice(0,4)}-${priorDateStr.slice(4,6)}-${priorDateStr.slice(6,8)}` : 
					priorDateStr;
				
				return {
					ProcessingDateKey: formattedDate,
					CommitmentAmt: row.CommitmentAmt || 0,
					Deals: row.Deals || 0,
					OutstandingAmt: row.OutstandingAmt || 0,
					ProcessingDateKeyPrior: formattedPriorDate,
					CommitmentAmtPrior: row.CommitmentAmtPrior || 0,
					OutstandingAmtPrior: row.OutstandingAmtPrior || 0,
					DealsPrior: row.DealsPrior || 0,
					ca_diff: row.ca_diff,
					oa_diff: row.oa_diff,
					deals_diff: row.deals_diff,
					ca_model_diff: row.ca_model_diff,
					oa_model_diff: row.oa_model_diff,
					deals_model_diff: row.deals_model_diff,
				};
			});
			
			setData(transformedData);
		} catch (e: any) {
			setErr(String(e?.message || e));
		}
	};

	useEffect(() => {
		load();
	}, []);

	return (
		<main className="p-6 space-y-4 bg-gradient-to-br from-slate-50 to-blue-50/20 min-h-screen">
			<div className="flex items-center justify-between">
				<h1 className="text-2xl font-bold text-slate-900">Data Analysis</h1>
				<Badge variant="default" className="bg-gradient-to-r from-emerald-600 to-green-600 text-white">
					testCappedvsUncapped Results
				</Badge>
			</div>
			{err && <p className="text-red-600">{err}</p>}
			{data.length > 0 && <DataTable data={data} />}
		</main>
	);
}