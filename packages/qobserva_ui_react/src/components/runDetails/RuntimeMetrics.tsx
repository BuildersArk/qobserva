import MetricCard from '../MetricCard';

interface Props {
  runtimeMs: number;
  queueMs: number;
  shots: number;
  runtimePerShot: number;
  classification: 'cpu-bound' | 'queue-dominated' | 'execution-dominated' | 'unknown';
}

export default function RuntimeMetrics({ runtimeMs, queueMs, runtimePerShot, classification }: Props) {
  const getClassificationColor = (cls: string) => {
    switch (cls) {
      case 'queue-dominated':
        return 'text-warning';
      case 'execution-dominated':
        return 'text-primary';
      case 'cpu-bound':
        return 'text-success';
      default:
        return 'text-dark-text-muted';
    }
  };

  const getClassificationLabel = (cls: string) => {
    switch (cls) {
      case 'queue-dominated':
        return 'Queue-Dominated';
      case 'execution-dominated':
        return 'Execution-Dominated';
      case 'cpu-bound':
        return 'CPU-Bound';
      default:
        return 'Unknown';
    }
  };

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Runtime & Execution Behavior</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Runtime analysis helps identify if backend is slow or circuit is slow. Classification is heuristic.
      </p>
      <div className="grid grid-cols-4 gap-4 mb-4">
        <MetricCard 
          label="Runtime" 
          value={`${runtimeMs.toLocaleString()}ms`}
        />
        <MetricCard 
          label="Queue Time" 
          value={`${queueMs.toLocaleString()}ms`}
        />
        <MetricCard 
          label="Runtime/Shot" 
          value={`${runtimePerShot.toFixed(3)}ms`}
        />
        <div className="metric-card">
          <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
            Classification
          </div>
          <div className={`text-2xl font-bold ${getClassificationColor(classification)}`}>
            {getClassificationLabel(classification)}
          </div>
        </div>
      </div>
      <div className="mt-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-dark-text-muted">Time Distribution:</span>
        </div>
        <div className="w-full bg-dark-bg rounded-full h-4 flex overflow-hidden">
          {runtimeMs > 0 && queueMs > 0 && (
            <>
              <div 
                className="bg-primary h-4 transition-all"
                style={{ width: `${(runtimeMs / (runtimeMs + queueMs)) * 100}%` }}
                title={`Execution: ${runtimeMs}ms`}
              />
              <div 
                className="bg-warning h-4 transition-all"
                style={{ width: `${(queueMs / (runtimeMs + queueMs)) * 100}%` }}
                title={`Queue: ${queueMs}ms`}
              />
            </>
          )}
        </div>
        <div className="flex justify-between text-xs text-dark-text-muted mt-2">
          <span>Execution: {runtimeMs}ms</span>
          <span>Queue: {queueMs}ms</span>
        </div>
      </div>
      {classification === 'queue-dominated' && (
        <p className="text-sm text-warning mt-4">
          ⚠️ Queue time dominates - Backend may be heavily loaded
        </p>
      )}
    </div>
  );
}
