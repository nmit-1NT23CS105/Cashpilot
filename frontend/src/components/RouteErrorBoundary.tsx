import React from 'react';
import { StatusScreen } from './StatusScreen';

interface RouteErrorBoundaryProps { children: React.ReactNode; }
interface RouteErrorBoundaryState { hasError: boolean; }

export class RouteErrorBoundary extends React.Component<RouteErrorBoundaryProps, RouteErrorBoundaryState> {
    state: RouteErrorBoundaryState = { hasError: false };

    static getDerivedStateFromError(): RouteErrorBoundaryState {
        return { hasError: true };
    }

    render() {
        if (this.state.hasError) {
            return <StatusScreen title="This AI page could not open" message="Your business data is safe. Reload the workspace and try again." actionLabel="Reload workspace" onAction={() => window.location.reload()} />;
        }
        return this.props.children;
    }
}