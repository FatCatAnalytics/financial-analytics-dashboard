"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ChartVisualization } from "@/components/ChartVisualization";
import { AnalyticsData } from "@/types/data";
import { Badge } from "@/components/ui/badge";

export default function CompositesPage() {
	const [chartData, setChartData] = useState<AnalyticsData[]>([]);
	const [composites, setComposites] = useState<any>(null);
	const [err, setErr] = useState<string>("");

	useEffect(() => {
		// Use capped analysis for comprehensive composite visualization
		api.cappedAnalysis({
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
			output_file: `composites_analysis_${Date.now()}.csv`
		}).then(analysisResult => {
			console.log("Capped analysis loaded from:", analysisResult.source || "database");
			
			if (analysisResult.error) {
				setErr(analysisResult.error);
				return;
			}
			
			const r = {
				series: analysisResult.analysis_results,
				source: analysisResult.source
			};
			// Transform capped analysis results for ChartVisualization
			const transformed = r.series.map((row: any) => {
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
					OutstandingAmt: row.OutstandingAmt || 0,
					Deals: row.Deals || 0,
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
			
			setChartData(transformed);
			setComposites(r);
		}).catch(e => setErr(String(e)));
	}, []);

	return (
		<main className="p-6 space-y-6 bg-gradient-to-br from-slate-50 to-blue-50/20 min-h-screen">
			<div className="flex items-center justify-between">
				<h1 className="text-3xl font-bold text-slate-900">Composites Analysis</h1>
				<Badge variant="default" className="bg-gradient-to-r from-emerald-600 to-green-600 text-white">
					testCappedvsUncapped Results
				</Badge>
			</div>
			{err && <p className="text-red-600">{err}</p>}
			
			{chartData.length > 0 && (
				<ChartVisualization data={chartData} />
			)}
			
			{composites && composites.series && (
				<div className="mt-8 bg-white/90 backdrop-blur-sm p-6 rounded-xl shadow-lg border border-slate-200/50">
					<h2 className="font-semibold text-lg mb-3 text-slate-800">Raw Composite Series Data</h2>
					<div className="overflow-x-auto">
						<table className="min-w-full text-sm">
							<thead>
								<tr className="border-b">
									<th className="text-left py-2 px-3">Date</th>
									<th className="text-right py-2 px-3">Commitment Amount</th>
									<th className="text-right py-2 px-3">Outstanding Amount</th>
									<th className="text-right py-2 px-3">Deals</th>
								</tr>
							</thead>
							<tbody>
								{composites.series.slice(0, 20).map((r: any, i: number) => (
									<tr key={i} className="border-b last:border-b-0 hover:bg-slate-50">
										<td className="py-2 px-3">{String(r.ProcessingDateKey)}</td>
										<td className="text-right py-2 px-3">{String(r.ca)}</td>
										<td className="text-right py-2 px-3">{String(r.oa)}</td>
										<td className="text-right py-2 px-3">{String(r.deals)}</td>
									</tr>
								))}
							</tbody>
						</table>
					</div>
				</div>
			)}
		</main>
	);
}