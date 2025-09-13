import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { X, Filter } from 'lucide-react';
import type { FilterOptions, SelectedFilters, CustomCommitmentRange } from '../types/data';
import { CustomCommitmentRangeBuilder } from './CustomCommitmentRangeBuilder';

interface FilterPanelProps {
  filterOptions: FilterOptions;
  selectedFilters: SelectedFilters;
  onFilterChange: (filterType: keyof SelectedFilters, values: string[]) => void;
  onCustomRangeAdd: (range: CustomCommitmentRange) => void;
  onCustomRangeRemove: (id: string) => void;
  onClearFilters: () => void;
  onRunQuery: () => void;
  disabled?: boolean;
}

export function FilterPanel({
  filterOptions,
  selectedFilters,
  onFilterChange,
  onCustomRangeAdd,
  onCustomRangeRemove,
  onClearFilters,
  onRunQuery,
  disabled = false
}: FilterPanelProps) {
  const handleSelectChange = (filterType: keyof SelectedFilters, value: string) => {
    // Skip customCommitmentRanges as they are handled differently
    if (filterType === 'customCommitmentRanges') return;
    
    const current = selectedFilters[filterType] as string[];
    if (!current.includes(value)) {
      onFilterChange(filterType, [...current, value]);
    }
  };

  const removeFilter = (filterType: keyof SelectedFilters, value: string) => {
    // Skip customCommitmentRanges as they are handled differently
    if (filterType === 'customCommitmentRanges') return;
    
    const current = selectedFilters[filterType] as string[];
    onFilterChange(filterType, current.filter(v => v !== value));
  };

  const filterLabels: Record<keyof FilterOptions, string> = {
    sbaClassification: 'SBA Classification',
    lineOfBusiness: 'Line of Business',
    commitmentSizeGroup: 'Commitment Size Group',
    riskGroup: 'Risk Group',
    bankId: 'Bank ID',
    region: 'Region',
    naicsGrpName: 'NAICS Group Name'
  };

  const totalSelectedFilters = Object.entries(selectedFilters).reduce((acc, [key, value]) => {
    if (key === 'customCommitmentRanges') {
      return acc + (value as CustomCommitmentRange[]).length;
    }
    return acc + (value as string[]).length;
  }, 0);

  return (
    <Card className="w-full border-0 bg-transparent shadow-none">
      <CardHeader className="pb-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-slate-700 to-blue-700 rounded-xl">
            <Filter className="w-5 h-5 text-white" />
          </div>
          <div>
            <CardTitle className="text-xl">Filter & Query Builder</CardTitle>
            <div className="text-sm text-muted-foreground">
              Select criteria to filter your analytics data and build custom queries
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-8">
        <div className="bg-white/70 backdrop-blur-sm rounded-xl border border-slate-200/40 p-6">
          <h4 className="font-medium mb-4 flex items-center gap-2">
            <div className="w-2 h-2 bg-blue-500 rounded-full" />
            Standard Filters
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {Object.entries(filterOptions).map(([filterType, options]) => {
            const filterKey = filterType as keyof FilterOptions;
            const selectedValues = selectedFilters[filterKey] as string[];
            
            return (
              <div key={filterType} className="space-y-2">
                <Label htmlFor={filterType}>
                  {filterLabels[filterKey]}
                </Label>
                <Select onValueChange={(value: string) => handleSelectChange(filterKey, value)}>
                  <SelectTrigger>
                    <SelectValue placeholder={`Select ${filterLabels[filterKey]}`} />
                  </SelectTrigger>
                  <SelectContent>
                    {options.map((option: string) => (
                      <SelectItem 
                        key={option} 
                        value={option}
                        disabled={selectedValues.includes(option)}
                      >
                        {option}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                
                {selectedValues.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {selectedValues.map((value: string) => (
                      <Badge key={value} variant="secondary" className="text-sm">
                        {value}
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-4 w-4 p-0 ml-1"
                          onClick={() => removeFilter(filterKey, value)}
                        >
                          <X className="h-3 w-3" />
                        </Button>
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
          </div>
        </div>

        <div className="bg-white/70 backdrop-blur-sm rounded-xl border border-slate-200/40 p-6">
          <h4 className="font-medium mb-4 flex items-center gap-2">
            <div className="w-2 h-2 bg-cyan-500 rounded-full" />
            Custom Commitment Ranges
          </h4>
          <CustomCommitmentRangeBuilder
            customRanges={selectedFilters.customCommitmentRanges}
            onAddRange={onCustomRangeAdd}
            onRemoveRange={onCustomRangeRemove}
          />
        </div>

        <div className="bg-gradient-to-r from-slate-50/80 to-blue-50/30 rounded-xl border border-slate-200/50 p-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <div className="w-2 h-2 bg-blue-500 rounded-full" />
                <span className="text-sm font-medium">
                  {totalSelectedFilters} filters selected
                </span>
              </div>
              {totalSelectedFilters > 0 && (
                <Button variant="outline" size="sm" onClick={onClearFilters} className="bg-white/70">
                  Clear All Filters
                </Button>
              )}
            </div>
            <Button 
              onClick={onRunQuery} 
              disabled={disabled || totalSelectedFilters === 0}
              className="bg-gradient-to-r from-slate-700 to-blue-700 hover:from-slate-800 hover:to-blue-800 text-white font-medium px-6"
            >
              {disabled ? 'Database Required' : totalSelectedFilters === 0 ? 'Select Filters First' : 'Execute Query'}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}