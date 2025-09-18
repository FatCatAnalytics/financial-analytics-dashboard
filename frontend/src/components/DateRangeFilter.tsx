import { useState } from 'react';
import { Calendar } from './ui/calendar';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Badge } from './ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { CalendarIcon, X, Plus } from 'lucide-react';
import { format } from 'date-fns';
import type { DateFilter } from '../types/data';

interface DateRangeFilterProps {
  dateFilters: DateFilter[];
  onAddDateFilter: (filter: DateFilter) => void;
  onRemoveDateFilter: (index: number) => void;
}

export function DateRangeFilter({ 
  dateFilters, 
  onAddDateFilter, 
  onRemoveDateFilter 
}: DateRangeFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedOperator, setSelectedOperator] = useState<'equals' | 'greaterThan' | 'lessThan' | 'between'>('equals');
  const [startDate, setStartDate] = useState<Date | undefined>(undefined);
  const [endDate, setEndDate] = useState<Date | undefined>(undefined);

  const operatorLabels = {
    equals: 'Equals',
    greaterThan: 'Greater Than or Equal',
    lessThan: 'Less Than or Equal',
    between: 'Between'
  };

  const handleAddFilter = () => {
    if (!startDate) return;

    const newFilter: DateFilter = {
      operator: selectedOperator,
      startDate,
      ...(selectedOperator === 'between' && endDate ? { endDate } : {})
    };

    onAddDateFilter(newFilter);
    
    // Reset form
    setStartDate(undefined);
    setEndDate(undefined);
    setIsOpen(false);
  };

  const formatDateFilter = (filter: DateFilter, index: number) => {
    const operatorLabel = operatorLabels[filter.operator];
    const startDateStr = format(filter.startDate, 'MMM dd, yyyy');
    
    let description = `Processing Date ${operatorLabel.toLowerCase()} ${startDateStr}`;
    
    if (filter.operator === 'between' && filter.endDate) {
      const endDateStr = format(filter.endDate, 'MMM dd, yyyy');
      description = `Processing Date between ${startDateStr} and ${endDateStr}`;
    }

    return (
      <Badge key={index} variant="secondary" className="text-sm">
        {description}
        <Button
          variant="ghost"
          size="sm"
          className="h-4 w-4 p-0 ml-2"
          onClick={() => onRemoveDateFilter(index)}
        >
          <X className="h-3 w-3" />
        </Button>
      </Badge>
    );
  };

  const isFormValid = startDate && (selectedOperator !== 'between' || endDate);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h4 className="font-medium flex items-center gap-2">
          <div className="w-2 h-2 bg-green-500 rounded-full" />
          Processing Date Filters
        </h4>
        <Popover open={isOpen} onOpenChange={setIsOpen}>
          <PopoverTrigger asChild>
            <Button variant="outline" size="sm" className="bg-white/70">
              <Plus className="h-4 w-4 mr-1" />
              Add Date Filter
            </Button>
          </PopoverTrigger>
          <PopoverContent className="w-96 p-0" align="end">
            <Card className="border-0 shadow-lg">
              <CardHeader className="pb-4">
                <CardTitle className="text-lg">Add Processing Date Filter</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Operator</Label>
                  <Select value={selectedOperator} onValueChange={(value: 'equals' | 'greaterThan' | 'lessThan' | 'between') => setSelectedOperator(value)}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="equals">Equals</SelectItem>
                      <SelectItem value="greaterThan">≥ Greater Than or Equal</SelectItem>
                      <SelectItem value="lessThan">≤ Less Than or Equal</SelectItem>
                      <SelectItem value="between">Between</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>
                    {selectedOperator === 'between' ? 'Start Date' : 'Date'}
                  </Label>
                  <Popover>
                    <PopoverTrigger asChild>
                      <Button
                        variant="outline"
                        className="w-full justify-start text-left font-normal"
                      >
                        <CalendarIcon className="mr-2 h-4 w-4" />
                        {startDate ? format(startDate, 'PPP') : 'Select date'}
                      </Button>
                    </PopoverTrigger>
                    <PopoverContent className="w-auto p-0" align="start">
                      <Calendar
                        mode="single"
                        selected={startDate}
                        onSelect={setStartDate}
                        initialFocus
                      />
                    </PopoverContent>
                  </Popover>
                </div>

                {selectedOperator === 'between' && (
                  <div className="space-y-2">
                    <Label>End Date</Label>
                    <Popover>
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          className="w-full justify-start text-left font-normal"
                        >
                          <CalendarIcon className="mr-2 h-4 w-4" />
                          {endDate ? format(endDate, 'PPP') : 'Select end date'}
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={endDate}
                          onSelect={setEndDate}
                          initialFocus
                          disabled={(date: Date) => startDate ? date < startDate : false}
                        />
                      </PopoverContent>
                    </Popover>
                  </div>
                )}

                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button variant="outline" onClick={() => setIsOpen(false)}>
                    Cancel
                  </Button>
                  <Button 
                    onClick={handleAddFilter}
                    disabled={!isFormValid}
                    className="bg-gradient-to-r from-green-600 to-green-700 hover:from-green-700 hover:to-green-800 text-white"
                  >
                    Add Filter
                  </Button>
                </div>
              </CardContent>
            </Card>
          </PopoverContent>
        </Popover>
      </div>

      {dateFilters.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {dateFilters.map((filter, index) => formatDateFilter(filter, index))}
        </div>
      )}
    </div>
  );
}
