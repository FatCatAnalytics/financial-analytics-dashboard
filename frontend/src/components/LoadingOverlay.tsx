import React from 'react';
import { Card, CardContent } from './ui/card';
import { Skeleton } from './ui/skeleton';
import { Database, Search, BarChart3 } from 'lucide-react';

interface LoadingOverlayProps {
  type: 'filters' | 'query' | 'connection';
  message?: string;
}

export function LoadingOverlay({ type, message }: LoadingOverlayProps) {
  const getLoadingConfig = () => {
    switch (type) {
      case 'filters':
        return {
          icon: Database,
          title: 'Loading Filter Options',
          defaultMessage: 'Fetching available filters from database...',
          color: 'text-blue-500'
        };
      case 'query':
        return {
          icon: Search,
          title: 'Running Query',
          defaultMessage: 'Executing query and processing results...',
          color: 'text-green-500'
        };
      case 'connection':
        return {
          icon: Database,
          title: 'Connecting to Database',
          defaultMessage: 'Establishing database connection...',
          color: 'text-purple-500'
        };
      default:
        return {
          icon: Database,
          title: 'Loading',
          defaultMessage: 'Please wait...',
          color: 'text-muted-foreground'
        };
    }
  };

  const config = getLoadingConfig();
  const Icon = config.icon;

  return (
    <div className="flex items-center justify-center py-12">
      <div className="flex flex-col items-center gap-4 text-center max-w-md">
        <div className={`p-4 rounded-full bg-muted/50 ${config.color}`}>
          <Icon className="w-8 h-8" />
        </div>
        
        <div className="space-y-2">
          <h3 className="font-medium">{config.title}</h3>
          <p className="text-sm text-muted-foreground">
            {message || config.defaultMessage}
          </p>
        </div>
        
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.3s]" />
          <div className="w-2 h-2 bg-current rounded-full animate-bounce [animation-delay:-0.15s]" />
          <div className="w-2 h-2 bg-current rounded-full animate-bounce" />
        </div>
      </div>
    </div>
  );
}

export function FilterLoadingSkeleton() {
  return (
    <Card className="w-full">
      <CardContent className="p-6 space-y-6">
        <div className="space-y-2">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-1 w-full" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
        
        <div className="space-y-3">
          <Skeleton className="h-4 w-48" />
          <Skeleton className="h-16 w-full" />
        </div>
        
        <div className="flex items-center justify-between pt-4">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-10 w-24" />
        </div>
      </CardContent>
    </Card>
  );
}

export function DataLoadingSkeleton() {
  return (
    <Card className="w-full">
      <CardContent className="p-6 space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-32" />
        </div>
        
        <div className="space-y-3">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="flex items-center space-x-4">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-6 w-16" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function ChartLoadingSkeleton() {
  return (
    <Card className="w-full">
      <CardContent className="p-6 space-y-4">
        <div className="space-y-2">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div className="space-y-2">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-6 w-32" />
                  </div>
                  <div className="flex items-center gap-1">
                    <Skeleton className="h-4 w-4" />
                    <Skeleton className="h-5 w-12" />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
        
        <Skeleton className="h-96 w-full" />
      </CardContent>
    </Card>
  );
}
