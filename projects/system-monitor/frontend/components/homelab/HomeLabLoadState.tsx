interface HomeLabLoadStateProps {
  mode: 'loading' | 'failed';
  error?: string | null;
  onRetry?: () => void;
}

export function HomeLabLoadState({
  mode,
  error,
  onRetry,
}: HomeLabLoadStateProps) {
  if (mode === 'loading') {
    return (
      <div className="homelab-load-state" role="status" aria-live="polite">
        <div className="homelab-load-indicator" aria-hidden="true" />
        <h2 className="homelab-load-title">Loading Home Lab data…</h2>
        <p className="homelab-load-body">
          Connecting to the monitoring backend.
        </p>
      </div>
    );
  }

  return (
    <div className="homelab-load-state homelab-load-state-failed" role="alert">
      <h2 className="homelab-load-title">Unable to load Home Lab data</h2>
      <p className="homelab-load-body">
        The monitoring backend could not be reached.
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
