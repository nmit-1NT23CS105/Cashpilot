import React from 'react';
import { StatusScreen } from './StatusScreen';

interface AppErrorBoundaryProps { children: React.ReactNode; }
interface AppErrorBoundaryState { hasError: boolean; }

export class AppErrorBoundary extends React.Component<AppErrorBoundaryProps, AppErrorBoundaryState> {
    state: AppErrorBoundaryState = { hasError: false };
    static getDerivedStateFromError(): AppErrorBoundaryState { return { hasError: true }; }
    render() {
        if (this.state.hasError) return <StatusScreen title="This page stopped working" message="Your data is safe. Reload the workspace and try again." actionLabel="Reload workspace" onAction={() => window.location.reload()} />;
        return this.props.children;
    }
}