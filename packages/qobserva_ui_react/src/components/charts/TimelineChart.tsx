// TimelineChart - simple visual representation

interface Props {
  queueTime?: number;
  runtime?: number;
}

export default function TimelineChart({ queueTime, runtime }: Props) {
  const totalTime = (queueTime || 0) + (runtime || 0);
  
  if (!queueTime && !runtime) {
    return <div className="text-center py-12 text-dark-text-muted">No timeline data</div>;
  }

  return (
    <div className="space-y-4">
      {queueTime && (
        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm text-dark-text-muted">Queue Time</span>
            <span className="text-sm text-dark-text">{queueTime}ms</span>
          </div>
          <div className="h-4 bg-dark-bg rounded-full overflow-hidden">
            <div
              className="h-full bg-warning"
              style={{ width: `${(queueTime / totalTime) * 100}%` }}
            />
          </div>
        </div>
      )}
      
      {runtime && (
        <div>
          <div className="flex justify-between mb-2">
            <span className="text-sm text-dark-text-muted">Runtime</span>
            <span className="text-sm text-dark-text">{runtime}ms</span>
          </div>
          <div className="h-4 bg-dark-bg rounded-full overflow-hidden">
            <div
              className="h-full bg-success"
              style={{ width: `${(runtime / totalTime) * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
