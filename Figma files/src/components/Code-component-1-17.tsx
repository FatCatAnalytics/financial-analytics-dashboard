import React from 'react';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { X } from 'lucide-react';
import { FilterOptions, SelectedFilters } from '../types/data';

interface FilterPanelProps {
  filterOptions: FilterOptions;
  selectedFilters: SelectedFilters;
  onFilterChange: (filterType: keyof SelectedFilters, values: string[]) => void;
  onClearFilters: () => void;
  onRunQuery: () => void;
}

export function FilterPanel({
  filterOptions,
  selectedFilters,
  onFilterChange,
  onClearFilters,
  onRunQuery
}: FilterPanelProps) {
  const handleSelectChange = (filterType: keyof SelectedFilters, value: string) => {
    const current = selectedFilters[filterType];
    if (!current.includes(value)) {
      onFilterChange(filterType, [...current, value]);
    }
  };

  const removeFilter = (filterType: keyof SelectedFilters, value: string) => {
    onFilterChange(filterType, selectedFilters[filterType].filter(v => v !== value));
  };

  const filterLabels = {
    lineOfBusiness: 'Line of Business',
    commitmentSizeGroup: 'Commitment Size Group',
    riskGroup: 'Risk Group',
    bankId: 'Bank ID',
    region: 'Region',
    naicsGrpName: 'NAICS Group Name'
  };

  const totalSelectedFilters = Object.values(selectedFilters).reduce((acc, curr) => acc + curr.length, 0);

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle>Filter Options</CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Object.entries(filterOptions).map(([filterType, options]) => (
            <div key={filterType} className="space-y-2">
              <Label htmlFor={filterType}>
                {filterLabels[filterType as keyof FilterOptions]}
              </Label>
              <Select onValueChange={(value) => handleSelectChange(filterType as keyof SelectedFilters, value)}>
                <SelectTrigger>
                  <SelectValue placeholder={`Select ${filterLabels[filterType as keyof FilterOptions]}`} />
                </SelectTrigger>
                <SelectContent>
                  {options.map((option) => (
                    <SelectItem 
                      key={option} 
                      value={option}
                      disabled={selectedFilters[filterType as keyof SelectedFilters].includes(option)}
                    >
                      {option}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              
              {selectedFilters[filterType as keyof SelectedFilters].length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {selectedFilters[filterType as keyof SelectedFilters].map((value) => (
                    <Badge key={value} variant="secondary" className="text-sm">
                      {value}
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-4 w-4 p-0 ml-1"
                        onClick={() => removeFilter(filterType as keyof SelectedFilters, value)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="flex items-center justify-between pt-4 border-t">
          <div className="flex items-center gap-2">
            <span className="text-sm text-muted-foreground">
              {totalSelectedFilters} filters selected
            </span>
            {totalSelectedFilters > 0 && (
              <Button variant="outline" size="sm" onClick={onClearFilters}>
                Clear All
              </Button>
            )}
          </div>
          <Button onClick={onRunQuery} disabled={totalSelectedFilters === 0}>
            Run Query
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}