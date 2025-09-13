import React, { useState } from 'react';
import { Button } from './ui/button';
import { Input } from './ui/input';
import { Label } from './ui/label';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from './ui/dialog';
import { Plus, X, DollarSign } from 'lucide-react';
import { CustomCommitmentRange } from '../types/data';

interface CustomCommitmentRangeBuilderProps {
  customRanges: CustomCommitmentRange[];
  onAddRange: (range: CustomCommitmentRange) => void;
  onRemoveRange: (id: string) => void;
}

export function CustomCommitmentRangeBuilder({
  customRanges,
  onAddRange,
  onRemoveRange
}: CustomCommitmentRangeBuilderProps) {
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [rangeForm, setRangeForm] = useState({
    label: '',
    min: '',
    max: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const minValue = parseFloat(rangeForm.min);
    const maxValue = parseFloat(rangeForm.max);
    
    if (isNaN(minValue) || isNaN(maxValue) || minValue >= maxValue || !rangeForm.label.trim()) {
      return;
    }

    const newRange: CustomCommitmentRange = {
      id: `custom-${Date.now()}`,
      label: rangeForm.label.trim(),
      min: minValue,
      max: maxValue
    };

    onAddRange(newRange);
    setRangeForm({ label: '', min: '', max: '' });
    setIsDialogOpen(false);
  };

  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(1)}K`;
    }
    return `$${value.toLocaleString()}`;
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>Custom Commitment Ranges</Label>
        <Dialog open={isDialogOpen} onOpenChange={setIsDialogOpen}>
          <DialogTrigger asChild>
            <Button variant="outline" size="sm" className="flex items-center gap-1">
              <Plus className="w-4 h-4" />
              Add Range
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Create Custom Commitment Range</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="range-label">Range Label</Label>
                <Input
                  id="range-label"
                  placeholder="e.g., Mid-Market"
                  value={rangeForm.label}
                  onChange={(e) => setRangeForm(prev => ({ ...prev, label: e.target.value }))}
                  required
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="min-amount">Minimum Amount</Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="min-amount"
                      type="number"
                      placeholder="1000000"
                      className="pl-8"
                      value={rangeForm.min}
                      onChange={(e) => setRangeForm(prev => ({ ...prev, min: e.target.value }))}
                      required
                      min="0"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label htmlFor="max-amount">Maximum Amount</Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                    <Input
                      id="max-amount"
                      type="number"
                      placeholder="10000000"
                      className="pl-8"
                      value={rangeForm.max}
                      onChange={(e) => setRangeForm(prev => ({ ...prev, max: e.target.value }))}
                      required
                      min="0"
                    />
                  </div>
                </div>
              </div>
              
              <div className="flex justify-end gap-2 pt-4">
                <Button 
                  type="button" 
                  variant="outline" 
                  onClick={() => setIsDialogOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit">
                  Add Range
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {customRanges.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {customRanges.map((range) => (
            <Badge key={range.id} variant="secondary" className="flex items-center gap-1 pr-1">
              <span className="text-sm">
                {range.label}: {formatCurrency(range.min)} - {formatCurrency(range.max)}
              </span>
              <Button
                variant="ghost"
                size="sm"
                className="h-4 w-4 p-0 hover:bg-destructive hover:text-destructive-foreground"
                onClick={() => onRemoveRange(range.id)}
              >
                <X className="h-3 w-3" />
              </Button>
            </Badge>
          ))}
        </div>
      )}

      {customRanges.length === 0 && (
        <p className="text-sm text-muted-foreground">
          No custom ranges defined. Click "Add Range" to create one.
        </p>
      )}
    </div>
  );
}