"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DataTable } from "@/components/DataTable";
import { AnalyticsData } from "@/types/data";
import { BarChart3, Download, Play, Settings } from "lucide-react";

export default function AnalysisPage() {
	const [analysisResults, setAnalysisResults] = useState<AnalyticsData[]>([]);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState("");
	const [capValue, setCapValue] = useState(0.1);
	const [region, setRegion] = useState("Rocky Mountain");
	const [outputFile, setOutputFile] = useState("");
	const [lastAnalysis, setLastAnalysis] = useState<any>(null);

	const runCappedAnalysis = async () => {
		setIsLoading(true);
		setError("");
		
		try {
			const result = await api.cappedAnalysis({
				region: region,
				sba_filter: "Non-SBA",
				cap_value: capValue,
				output_file: outputFile || undefined,
				row_limit: 100,
			});
			
			if (result.error) {
				setError(result.error);
			} else {
				setAnalysisResults(result.analysis_results as AnalyticsData[]);
				setLastAnalysis(result);
			}
		} catch (e: any) {
			setError(e.message || "Analysis failed");
		} finally {
			setIsLoading(false);
		}
	};

	return (
		<main className="p-6 space-y-6 bg-gradient-to-br from-slate-50 to-blue-50/20 min-h-screen">
			<div className="flex items-center gap-3">
				<div className="p-3 bg-gradient-to-br from-slate-700 to-blue-700 rounded-xl">
					<BarChart3 className="w-6 h-6 text-white" />
				</div>
				<div>
					<h1 className="text-3xl font-bold text-slate-900">Capped vs Uncapped Analysis</h1>
					<p className="text-muted-foreground">
						Run the testCappedvsUncapped function to compare capped and uncapped composite analysis
					</p>
				</div>
			</div>

			{error && (
				<Card className="border-red-200 bg-red-50">
					<CardContent className="p-4">
						<p className="text-red-600">{error}</p>
					</CardContent>
				</Card>
			)}

			{/* Analysis Configuration */}
			<Card className="bg-white/90 backdrop-blur-sm border border-slate-200/50 shadow-lg">
				<CardHeader>
					<CardTitle className="flex items-center gap-2">
						<Settings className="w-5 h-5 text-slate-600" />
						Analysis Parameters
					</CardTitle>
				</CardHeader>
				<CardContent className="space-y-4">
					<div className="grid grid-cols-1 md:grid-cols-3 gap-4">
						<div className="space-y-2">
							<Label htmlFor="cap-value">Cap Value</Label>
							<Input
								id="cap-value"
								type="number"
								step="0.01"
								min="0"
								max="1"
								value={capValue}
								onChange={(e) => setCapValue(parseFloat(e.target.value) || 0.1)}
								placeholder="0.1 (10%)"
							/>
							<p className="text-xs text-muted-foreground">
								Percentage cap for composite analysis (e.g., 0.1 = 10%)
							</p>
						</div>
						
						<div className="space-y-2">
							<Label htmlFor="region">Region Filter</Label>
							<Input
								id="region"
								value={region}
								onChange={(e) => setRegion(e.target.value)}
								placeholder="Rocky Mountain"
							/>
						</div>
						
						<div className="space-y-2">
							<Label htmlFor="output-file">Output File (Optional)</Label>
							<Input
								id="output-file"
								value={outputFile}
								onChange={(e) => setOutputFile(e.target.value)}
								placeholder="capped_analysis.csv"
							/>
						</div>
					</div>
					
					<div className="flex items-center gap-4">
						<Button 
							onClick={runCappedAnalysis}
							disabled={isLoading}
							className="bg-gradient-to-r from-slate-700 to-blue-700 hover:from-slate-800 hover:to-blue-800"
						>
							{isLoading ? (
								<>
									<div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
									Running Analysis...
								</>
							) : (
								<>
									<Play className="w-4 h-4 mr-2" />
									Run Capped vs Uncapped Analysis
								</>
							)}
						</Button>
						
						{lastAnalysis && (
							<Badge variant="outline" className="bg-white/70">
								Last run: {lastAnalysis.record_count} records • Cap: {(lastAnalysis.parameters.cap_value * 100).toFixed(1)}%
							</Badge>
						)}
					</div>
				</CardContent>
			</Card>

			{/* Analysis Results */}
			{analysisResults.length > 0 && (
				<Card className="bg-white/90 backdrop-blur-sm border border-slate-200/50 shadow-lg">
					<CardHeader>
						<div className="flex items-center justify-between">
							<CardTitle className="flex items-center gap-2">
								<BarChart3 className="w-5 h-5 text-slate-600" />
								Analysis Results
							</CardTitle>
							{lastAnalysis?.output_file && (
								<Button variant="outline" size="sm" className="flex items-center gap-2">
									<Download className="w-4 h-4" />
									Download CSV: {lastAnalysis.output_file}
								</Button>
							)}
						</div>
						<p className="text-sm text-muted-foreground">
							Capped vs uncapped composite analysis results with period-over-period comparisons
						</p>
					</CardHeader>
					<CardContent>
						<div className="mb-4 p-4 bg-gradient-to-r from-slate-50/80 to-blue-50/30 rounded-xl border border-slate-200/50">
							<div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
								<div>
									<span className="font-medium">Records:</span> {lastAnalysis?.record_count || analysisResults.length}
								</div>
								<div>
									<span className="font-medium">Cap Value:</span> {(capValue * 100).toFixed(1)}%
								</div>
								<div>
									<span className="font-medium">Region:</span> {region}
								</div>
								<div>
									<span className="font-medium">Source:</span> 
									<Badge variant={lastAnalysis?.source === "database" ? "default" : "secondary"} className="ml-1 text-xs">
										{lastAnalysis?.source || "unknown"}
									</Badge>
								</div>
							</div>
						</div>
						
						<DataTable data={analysisResults} />
					</CardContent>
				</Card>
			)}

			{/* Empty State */}
			{analysisResults.length === 0 && !isLoading && (
				<Card className="bg-white/90 backdrop-blur-sm border border-slate-200/50 shadow-lg">
					<CardContent className="p-12 text-center">
						<div className="space-y-4 max-w-md mx-auto">
							<div className="w-16 h-16 bg-gradient-to-br from-slate-100 to-blue-100 rounded-2xl flex items-center justify-center mx-auto">
								<BarChart3 className="w-8 h-8 text-slate-600" />
							</div>
							<div>
								<h3 className="text-lg font-semibold">Ready for Analysis</h3>
								<p className="text-muted-foreground">
									Configure your parameters above and click "Run Analysis" to execute the capped vs uncapped comparison
								</p>
							</div>
						</div>
					</CardContent>
				</Card>
			)}
		</main>
	);
}
