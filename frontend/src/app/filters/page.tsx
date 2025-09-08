"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { FilterPanel } from "@/components/FilterPanel";
import { FilterOptions, SelectedFilters, CustomCommitmentRange } from "@/types/data";

export default function FiltersPage() {
	const [options, setOptions] = useState<FilterOptions>({
		lineOfBusiness: [],
		commitmentSizeGroup: [],
		riskGroup: [],
		bankId: [],
		region: [],
		naicsGrpName: [],
	});
	const [selected, setSelected] = useState<SelectedFilters>({
		lineOfBusiness: [],
		commitmentSizeGroup: [],
		riskGroup: [],
		bankId: [],
		region: [],
		naicsGrpName: [],
		customCommitmentRanges: [],
	});
	const [disabled, setDisabled] = useState(false);
	const [err, setErr] = useState("");

	useEffect(() => {
		api.filters(true).then((data) => {
			console.log("Filters loaded from:", data.source || "database");
			setOptions(data as unknown as FilterOptions);
		}).catch(e => setErr(String(e)));
	}, []);

	const onFilterChange = (filterType: keyof SelectedFilters, values: string[]) => {
		setSelected((s) => ({ ...s, [filterType]: values }));
	};

	const onRunQuery = async () => {
		setErr("");
		setDisabled(true);
		try {
			// Run capped analysis with current filters
			const analysisResult = await api.cappedAnalysis({
				selected_columns: ["ProcessingDateKey", "CommitmentAmt", "OutstandingAmt", "Deals"],
				region: selected.region[0] || "Rocky Mountain",
				sba_filter: "Non-SBA",
				line_of_business_ids: selected.lineOfBusiness.length > 0 ? selected.lineOfBusiness : undefined,
				commitment_size_groups: selected.commitmentSizeGroup.length > 0 ? selected.commitmentSizeGroup : undefined,
				risk_group_descriptions: selected.riskGroup.length > 0 ? selected.riskGroup : undefined,
				cap_value: 0.1,
				output_file: `filters_analysis_${Date.now()}.csv`
			});
			
			if (analysisResult.error) {
				setErr(analysisResult.error);
			} else {
				console.log(`Capped analysis completed: ${analysisResult.record_count} records from ${analysisResult.source}`);
			}
		} catch (e: any) {
			setErr(String(e?.message || e));
		} finally {
			setDisabled(false);
		}
	};

	return (
		<main className="p-6 space-y-4">
			<h1 className="text-xl font-semibold">Filters</h1>
			{err && <p className="text-red-600">{err}</p>}
			<FilterPanel
				filterOptions={options}
				selectedFilters={selected}
				onFilterChange={onFilterChange}
				onCustomRangeAdd={(r) => setSelected((s) => ({ ...s, customCommitmentRanges: [...s.customCommitmentRanges, r] }))}
				onCustomRangeRemove={(id) => setSelected((s) => ({ ...s, customCommitmentRanges: s.customCommitmentRanges.filter((range) => range.id !== id) }))}
				onClearFilters={() => setSelected({ lineOfBusiness: [], commitmentSizeGroup: [], riskGroup: [], bankId: [], region: [], naicsGrpName: [], customCommitmentRanges: [] })}
				onRunQuery={onRunQuery}
				disabled={disabled}
			/>
		</main>
	);
}
