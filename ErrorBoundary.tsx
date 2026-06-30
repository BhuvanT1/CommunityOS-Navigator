import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCcw } from 'lucide-react';

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="fixed inset-0 bg-zinc-950 text-white flex items-center justify-center p-6 z-[9999] font-sans">
          <div className="bg-zinc-900 border border-white/10 rounded-2xl p-8 max-w-md w-full shadow-2xl text-center">
            <div className="w-20 h-20 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
              <AlertTriangle className="w-10 h-10 text-red-500" />
            </div>
            
            <h1 className="text-2xl font-bold mb-3 tracking-tight">Something went wrong</h1>
            
            <p className="text-zinc-400 text-sm mb-8 leading-relaxed">
              An unexpected error occurred in the application. Please try refreshing the page. If the problem persists, contact support.
            </p>

            <button
              onClick={() => window.location.reload()}
              className="w-full bg-white text-zinc-950 font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 hover:bg-zinc-200 transition-colors shadow-xl"
            >
              <RefreshCcw className="w-5 h-5" />
              Reload Application
            </button>
            
            {this.state.error && (
              <div className="mt-8 text-left bg-black/50 p-4 rounded-lg overflow-x-auto">
                <p className="text-xs font-mono text-red-400 whitespace-pre-wrap break-all">
                  {this.state.error.toString()}
                </p>
              </div>
            )}
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
