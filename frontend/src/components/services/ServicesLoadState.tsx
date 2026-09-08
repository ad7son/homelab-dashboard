interface ServicesLoadStateProps {
  mode: 'loading' | 'failed';
  error?: string | null;
  onRetry?: () => void;
}

export function ServicesLoadState({
  mode,
  error,
  onRetry,
}: ServicesLoadStateProps) {
  if (mode === 'loading') {
    return (
      <div className="homelab-load-state" role="status" aria-live="polite">
        <div className="homelab-load-indicator" aria-hidden="true" />
        <h2 className="homelab-load-title">Loading service status…</h2>
        <p className="homelab-load-body">
          Fetching monitored systemd services from the backend.
        </p>
      </div>
    );
  }

  return (
    <div className="homelab-load-state homelab-load-state-failed" role="alert">
      <h2 className="homelab-load-title">Unable to load service status</h2>
      <p className="homelab-load-body">
        The services API could not be reached.
      </p>
      {error ? <p className="homelab-load-detail">{error}</p> : null}
      {onRetry ? (
        <button
          type="button"
          className="homelab-retry-button"
          onClick={onRetry}
        >
          Retry
        </button>
      ) : null}
    </div>
  );
}
