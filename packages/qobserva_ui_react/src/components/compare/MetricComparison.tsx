import { useMemo } from 'react';
import { Event, Analysis } from '../../services/api';
import { calculateRunMetrics } from '../../utils/runMetrics';

interface Props {
  runA: { event: Event; analysis: Analysis };
  runB: { event: Event; analysis: Analysis };
}

export default function MetricComparison({ runA, runB }: Props) {
  const metricsA = useMemo(() => calculateRunMetrics(runA.event, runA.analysis), [runA]);
  const metricsB = useMemo(() => calculateRunMetrics(runB.event, runB.analysis), [runB]);
  
  const analysisA = runA.analysis.metrics || {};
  const analysisB = runB.analysis.metrics || {};

  const formatDelta = (valA: number | undefined, valB: number | undefined, format: 'number' | 'percent' | 'ms' | 'usd' | 's' = 'number') => {
    if (valA === undefined || valB === undefined) return 'N/A';
    const delta = valB - valA;
    const sign = delta >= 0 ? '+' : '';
    
    if (format === 'percent') {
      return `${sign}${(delta * 100).toFixed(1)}%`;
    } else if (format === 'ms') {
      return `${sign}${delta.toFixed(0)}ms`;
    } else if (format === 'usd') {
      return `${sign}$${delta.toFixed(4)}`;
    } else if (format === 's') {
      return `${sign}${delta.toFixed(2)} s`;
    }
    return `${sign}${delta.toLocaleString()}`;
  };

  const getDeltaColor = (valA: number | undefined, valB: number | undefined, lowerIsBetter: boolean = false) => {
    if (valA === undefined || valB === undefined) return 'text-dark-text-muted';
    const delta = valB - valA;
    if (delta === 0) return 'text-dark-text-muted';
    if (lowerIsBetter) {
      return delta < 0 ? 'text-success' : 'text-error';
    }
    return delta > 0 ? 'text-success' : 'text-error';
  };

  return (
    <div className="space-y-6">
      {/* Basic Execution Metrics */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Basic Execution Metrics</h3>
        <p className="text-sm text-dark-text-muted mb-4">
          Comparing Run A vs Run B. Delta shows change from Run A to Run B (positive = Run B is higher, negative = Run B is lower).
        </p>
        <div className="grid grid-cols-4 gap-4">
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Shots
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-xl font-bold text-white">
                  {runA.event.execution.shots.toLocaleString()}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-xl font-bold text-white">
                  {runB.event.execution.shots.toLocaleString()}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(runA.event.execution.shots, runB.event.execution.shots)}`}>
                Δ: {formatDelta(runA.event.execution.shots, runB.event.execution.shots)}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Success Rate
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-xl font-bold text-white">
                  {analysisA['qc.quality.success_probability'] 
                    ? `${(analysisA['qc.quality.success_probability'] * 100).toFixed(1)}%` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-xl font-bold text-white">
                  {analysisB['qc.quality.success_probability'] 
                    ? `${(analysisB['qc.quality.success_probability'] * 100).toFixed(1)}%` 
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${
                getDeltaColor(
                  analysisA['qc.quality.success_probability'],
                  analysisB['qc.quality.success_probability']
                )
              }`}>
                Δ: {formatDelta(
                  analysisA['qc.quality.success_probability'],
                  analysisB['qc.quality.success_probability'],
                  'percent'
                )}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Runtime
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-xl font-bold text-white">
                  {runA.event.execution.runtime_ms 
                    ? `${runA.event.execution.runtime_ms.toLocaleString()}ms` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-xl font-bold text-white">
                  {runB.event.execution.runtime_ms 
                    ? `${runB.event.execution.runtime_ms.toLocaleString()}ms` 
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(runA.event.execution.runtime_ms, runB.event.execution.runtime_ms, true)}`}>
                Δ: {formatDelta(runA.event.execution.runtime_ms, runB.event.execution.runtime_ms, 'ms')}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Cost
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-xl font-bold text-white">
                  {analysisA['qc.cost.estimated_usd'] 
                    ? `$${analysisA['qc.cost.estimated_usd'].toFixed(4)}` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-xl font-bold text-white">
                  {analysisB['qc.cost.estimated_usd'] 
                    ? `$${analysisB['qc.cost.estimated_usd'].toFixed(4)}` 
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(analysisA['qc.cost.estimated_usd'], analysisB['qc.cost.estimated_usd'], true)}`}>
                Δ: {formatDelta(analysisA['qc.cost.estimated_usd'], analysisB['qc.cost.estimated_usd'], 'usd')}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Quality Metrics Comparison */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Quality Metrics</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Entropy
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {analysisA['qc.quality.shannon_entropy_bits']?.toFixed(4) || 'N/A'} bits
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {analysisB['qc.quality.shannon_entropy_bits']?.toFixed(4) || 'N/A'} bits
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(analysisA['qc.quality.shannon_entropy_bits'], analysisB['qc.quality.shannon_entropy_bits'])}`}>
                Δ: {formatDelta(analysisA['qc.quality.shannon_entropy_bits'], analysisB['qc.quality.shannon_entropy_bits'])}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Top-1 Probability
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {metricsA.top1Probability 
                    ? `${(metricsA.top1Probability * 100).toFixed(3)}%` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {metricsB.top1Probability 
                    ? `${(metricsB.top1Probability * 100).toFixed(3)}%` 
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(metricsA.top1Probability, metricsB.top1Probability)}`}>
                Δ: {formatDelta(metricsA.top1Probability, metricsB.top1Probability, 'percent')}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Effective Support
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {metricsA.effectiveSupportSize?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {metricsB.effectiveSupportSize?.toLocaleString() || 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(metricsA.effectiveSupportSize, metricsB.effectiveSupportSize)}`}>
                Δ: {formatDelta(metricsA.effectiveSupportSize, metricsB.effectiveSupportSize)}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Shot Efficiency Comparison */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Shot Efficiency</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Unique States
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {metricsA.uniqueStates?.toLocaleString() || 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {metricsB.uniqueStates?.toLocaleString() || 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(metricsA.uniqueStates, metricsB.uniqueStates)}`}>
                Δ: {formatDelta(metricsA.uniqueStates, metricsB.uniqueStates)}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Unique/Shots Ratio
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {metricsA.uniqueStatesRatio 
                    ? `${(metricsA.uniqueStatesRatio * 100).toFixed(2)}%` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {metricsB.uniqueStatesRatio 
                    ? `${(metricsB.uniqueStatesRatio * 100).toFixed(2)}%` 
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(metricsA.uniqueStatesRatio, metricsB.uniqueStatesRatio)}`}>
                Δ: {formatDelta(metricsA.uniqueStatesRatio, metricsB.uniqueStatesRatio, 'percent')}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Collision Rate
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {metricsA.collisionRate 
                    ? `${(metricsA.collisionRate * 100).toFixed(2)}%` 
                    : 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {metricsB.collisionRate 
                    ? `${(metricsB.collisionRate * 100).toFixed(2)}%` 
                    : 'N/A'}
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(metricsA.collisionRate, metricsB.collisionRate, true)}`}>
                Δ: {formatDelta(metricsA.collisionRate, metricsB.collisionRate, 'percent')}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Runtime Analysis Comparison */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Runtime Analysis</h3>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Runtime/Shot
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {metricsA.runtimePerShot?.toFixed(3) || 'N/A'} ms
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {metricsB.runtimePerShot?.toFixed(3) || 'N/A'} ms
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(metricsA.runtimePerShot, metricsB.runtimePerShot, true)}`}>
                Δ: {formatDelta(metricsA.runtimePerShot, metricsB.runtimePerShot, 'ms')}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Queue Time
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white">
                  {runA.event.execution.queue_ms?.toLocaleString() || 'N/A'} ms
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white">
                  {runB.event.execution.queue_ms?.toLocaleString() || 'N/A'} ms
                </span>
              </div>
            </div>
            <div className="mt-2 pt-2 border-t border-dark-border">
              <div className={`text-sm font-semibold ${getDeltaColor(runA.event.execution.queue_ms, runB.event.execution.queue_ms, true)}`}>
                Δ: {formatDelta(runA.event.execution.queue_ms, runB.event.execution.queue_ms, 'ms')}
              </div>
            </div>
          </div>
          
          <div>
            <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
              Classification
            </div>
            <div className="space-y-1">
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-primary font-medium">Run A:</span>
                <span className="text-lg font-bold text-white capitalize">
                  {metricsA.runtimeClassification || 'N/A'}
                </span>
              </div>
              <div className="flex items-baseline gap-2">
                <span className="text-xs text-success font-medium">Run B:</span>
                <span className="text-lg font-bold text-white capitalize">
                  {metricsB.runtimeClassification || 'N/A'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Execution time breakdown (CPU / QPU / queue_s / post_processing_s) when provided by backend */}
      {(analysisA['qc.time.cpu_s'] != null || analysisB['qc.time.cpu_s'] != null ||
        analysisA['qc.time.qpu_s'] != null || analysisB['qc.time.qpu_s'] != null ||
        analysisA['qc.time.queue_s'] != null || analysisB['qc.time.queue_s'] != null ||
        analysisA['qc.time.post_processing_s'] != null || analysisB['qc.time.post_processing_s'] != null) && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-2 text-white">Execution time breakdown</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Provider-reported CPU, QPU, queue, and post-processing time (seconds). Shown when the backend supplies this metadata.
          </p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {(analysisA['qc.time.cpu_s'] != null || analysisB['qc.time.cpu_s'] != null) && (
              <div>
                <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">CPU</div>
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-primary font-medium">Run A:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisA['qc.time.cpu_s'] != null ? `${Number(analysisA['qc.time.cpu_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-success font-medium">Run B:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisB['qc.time.cpu_s'] != null ? `${Number(analysisB['qc.time.cpu_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-dark-border">
                  <div className={`text-sm font-semibold ${getDeltaColor(analysisA['qc.time.cpu_s'], analysisB['qc.time.cpu_s'], true)}`}>
                    Δ: {formatDelta(analysisA['qc.time.cpu_s'], analysisB['qc.time.cpu_s'], 's')}
                  </div>
                </div>
              </div>
            )}
            {(analysisA['qc.time.qpu_s'] != null || analysisB['qc.time.qpu_s'] != null) && (
              <div>
                <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">QPU</div>
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-primary font-medium">Run A:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisA['qc.time.qpu_s'] != null ? `${Number(analysisA['qc.time.qpu_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-success font-medium">Run B:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisB['qc.time.qpu_s'] != null ? `${Number(analysisB['qc.time.qpu_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-dark-border">
                  <div className={`text-sm font-semibold ${getDeltaColor(analysisA['qc.time.qpu_s'], analysisB['qc.time.qpu_s'], true)}`}>
                    Δ: {formatDelta(analysisA['qc.time.qpu_s'], analysisB['qc.time.qpu_s'], 's')}
                  </div>
                </div>
              </div>
            )}
            {(analysisA['qc.time.queue_s'] != null || analysisB['qc.time.queue_s'] != null) && (
              <div>
                <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">Queue (provider)</div>
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-primary font-medium">Run A:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisA['qc.time.queue_s'] != null ? `${Number(analysisA['qc.time.queue_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-success font-medium">Run B:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisB['qc.time.queue_s'] != null ? `${Number(analysisB['qc.time.queue_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-dark-border">
                  <div className={`text-sm font-semibold ${getDeltaColor(analysisA['qc.time.queue_s'], analysisB['qc.time.queue_s'], true)}`}>
                    Δ: {formatDelta(analysisA['qc.time.queue_s'], analysisB['qc.time.queue_s'], 's')}
                  </div>
                </div>
              </div>
            )}
            {(analysisA['qc.time.post_processing_s'] != null || analysisB['qc.time.post_processing_s'] != null) && (
              <div>
                <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">Post-processing</div>
                <div className="space-y-1">
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-primary font-medium">Run A:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisA['qc.time.post_processing_s'] != null ? `${Number(analysisA['qc.time.post_processing_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                  <div className="flex items-baseline gap-2">
                    <span className="text-xs text-success font-medium">Run B:</span>
                    <span className="text-lg font-bold text-white">
                      {analysisB['qc.time.post_processing_s'] != null ? `${Number(analysisB['qc.time.post_processing_s']).toFixed(2)} s` : 'N/A'}
                    </span>
                  </div>
                </div>
                <div className="mt-2 pt-2 border-t border-dark-border">
                  <div className={`text-sm font-semibold ${getDeltaColor(analysisA['qc.time.post_processing_s'], analysisB['qc.time.post_processing_s'], true)}`}>
                    Δ: {formatDelta(analysisA['qc.time.post_processing_s'], analysisB['qc.time.post_processing_s'], 's')}
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
