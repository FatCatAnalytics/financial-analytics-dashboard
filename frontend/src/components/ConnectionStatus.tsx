import React from 'react';
import { Badge } from './ui/badge';
import { Card, CardContent } from './ui/card';
import { Wifi, WifiOff, Database, AlertCircle, CheckCircle2 } from 'lucide-react';

interface ConnectionStatusProps {
  isConnected: boolean;
  isConnecting: boolean;
  connectionType?: 'database' | 'api';
  lastConnectionTime?: Date;
  error?: string;
}

export function ConnectionStatus({ 
  isConnected, 
  isConnecting, 
  connectionType = 'database',
  lastConnectionTime,
  error 
}: ConnectionStatusProps) {
  const getStatusColor = () => {
    if (isConnecting) return 'secondary';
    if (error) return 'destructive';
    return isConnected ? 'default' : 'secondary';
  };

  const getStatusIcon = () => {
    if (isConnecting) {
      return <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />;
    }
    if (error) {
      return <AlertCircle className="w-3 h-3" />;
    }
    if (isConnected) {
      return connectionType === 'database' ? <Database className="w-3 h-3" /> : <Wifi className="w-3 h-3" />;
    }
    return connectionType === 'database' ? <Database className="w-3 h-3 opacity-50" /> : <WifiOff className="w-3 h-3" />;
  };

  const getStatusText = () => {
    if (isConnecting) return `Connecting to ${connectionType}...`;
    if (error) return `Connection error`;
    if (isConnected) return `${connectionType === 'database' ? 'Database' : 'API'} connected`;
    return `${connectionType === 'database' ? 'Database' : 'API'} disconnected`;
  };

  return (
    <div className="flex items-center gap-2">
      <Badge variant={getStatusColor()} className="flex items-center gap-1.5">
        {getStatusIcon()}
        <span className="text-xs">{getStatusText()}</span>
      </Badge>
      
      {isConnected && lastConnectionTime && (
        <span className="text-xs text-muted-foreground">
          Last sync: {lastConnectionTime.toLocaleTimeString()}
        </span>
      )}
      
      {error && (
        <span className="text-xs text-destructive" title={error}>
          {error.length > 30 ? `${error.substring(0, 30)}...` : error}
        </span>
      )}
    </div>
  );
}

export function ConnectionCard({ 
  isConnected, 
  isConnecting, 
  connectionType = 'database',
  lastConnectionTime,
  error,
  onRetry 
}: ConnectionStatusProps & { onRetry?: () => void }) {
  const getStatusText = () => {
    if (isConnecting) return `Connecting to ${connectionType}...`;
    if (error) return `Connection error`;
    if (isConnected) return `${connectionType === 'database' ? 'Database' : 'API'} connected`;
    return `${connectionType === 'database' ? 'Database' : 'API'} disconnected`;
  };

  return (
    <Card className={`border-l-4 ${
      error ? 'border-l-destructive' : 
      isConnected ? 'border-l-green-500' : 
      'border-l-muted'
    }`}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-full ${
              error ? 'bg-destructive/10' :
              isConnected ? 'bg-green-500/10' : 
              'bg-muted'
            }`}>
              {isConnecting ? (
                <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
              ) : error ? (
                <AlertCircle className="w-4 h-4 text-destructive" />
              ) : isConnected ? (
                <CheckCircle2 className="w-4 h-4 text-green-500" />
              ) : (
                <Database className="w-4 h-4 text-muted-foreground" />
              )}
            </div>
            
            <div>
              <p className="font-medium">
                {connectionType === 'database' ? 'PostgreSQL Database' : 'API Connection'}
              </p>
              <p className="text-sm text-muted-foreground">
                {getStatusText()}
              </p>
              {error && (
                <p className="text-xs text-destructive mt-1">{error}</p>
              )}
            </div>
          </div>
          
          <div className="text-right">
            {lastConnectionTime && (
              <p className="text-xs text-muted-foreground">
                {lastConnectionTime.toLocaleString()}
              </p>
            )}
            {error && onRetry && (
              <button 
                onClick={onRetry}
                className="text-xs text-primary hover:underline mt-1"
              >
                Retry connection
              </button>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
