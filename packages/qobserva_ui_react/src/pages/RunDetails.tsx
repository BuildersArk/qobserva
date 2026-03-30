import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import MetricCard from '../components/MetricCard';
import CountsChart from '../components/charts/CountsChart';
import TimelineChart from '../components/charts/TimelineChart';
import TopKDominance from '../components/runDetails/TopKDominance';
import EffectiveSupport from '../components/runDetails/EffectiveSupport';
import EntropyMetrics from '../components/runDetails/EntropyMetrics';
import ShotEfficiency from '../components/runDetails/ShotEfficiency';
import RuntimeMetrics from '../components/runDetails/RuntimeMetrics';
import ExecutionTimeBreakdown from '../components/runDetails/ExecutionTimeBreakdown';
import { calculateRunMetrics } from '../utils/runMetrics';
import { checkTagWarnings } from '../utils/tagWarnings';
import { ChevronDown, ChevronUp, AlertTriangle, Info } from 'lucide-react';
import CopyableRunId from '../components/CopyableRunId';

export default function RunDetails() {
  const { runId } = useParams<{ runId: string }>();
  const [expandedSections, setExpandedSections] = useState<Record<string, boolean>>({
    rawMetadata: false,
    rawEvent: false,
    rawAnalysis: false,
  });
  
  // Get run data - try to find project from runs list first
  const { data: runs = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: () => apiService.getRuns({ limit: 1000 }),
  });

  const run = runs.find(r => r.run_id === runId);
  const project = run?.project || 'default';

  const { data, isLoading, error } = useQuery({
    queryKey: ['run', runId],
    queryFn: () => apiService.getRun(project, runId!),
    enabled: !!runId,
    retry: 2,
  });

  // Calculate all run metrics - must be before conditional returns (Rules of Hooks)
  const runMetrics = useMemo(() => {
    if (!data) return {};
    return calculateRunMetrics(data.event, data.analysis);
  }, [data]);
  
  // Extract values safely - must be before conditional returns
  const event = data?.event;
  const analysis = data?.analysis;
  const metrics = analysis?.metrics || {};
  const entropy = metrics['qc.quality.shannon_entropy_bits'];
  const counts = event?.artifacts?.counts?.histogram || {};
  const totalStates = Object.keys(counts).length;
  
  // Check for tag-based warnings (conservative, only for clearly test/error scenarios)
  const tagWarning = useMemo(() => {
    if (!event?.tags) return null;
    return checkTagWarnings(event.tags);
  }, [event?.tags]);

  if (isLoading) {
    return <div className="text-center py-12 text-dark-text-muted">Loading...</div>;
  }

  if (error || !data || !event || !analysis) {
    return (
      <div className="text-center py-12">
        <p className="text-dark-text-muted mb-4">Run not found</p>
        <p className="text-sm text-dark-text-muted">Run ID: {runId}</p>
      </div>
    );
  }

  const toggleSection = (section: string) => {
    setExpandedSections(prev => ({
      ...prev,
      [section]: !prev[section],
    }));
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Run Details</h1>
        <div className="flex items-center gap-2">
          <span className="text-dark-text-muted">Run ID:</span>
          <CopyableRunId runId={runId || ''} truncate={false} />
        </div>
      </div>

      {/* Tag-based Warning (if applicable) */}
      {tagWarning && (
        <div className={`card border-l-4 ${
          tagWarning.severity === 'warn' 
            ? 'border-warning bg-warning/10' 
            : 'border-primary bg-primary/10'
        }`}>
          <div className="flex items-start gap-3">
            {tagWarning.severity === 'warn' ? (
              <AlertTriangle className="text-warning mt-0.5 flex-shrink-0" size={20} />
            ) : (
              <Info className="text-primary mt-0.5 flex-shrink-0" size={20} />
            )}
            <div className="flex-1">
              <h4 className={`font-semibold mb-1 ${
                tagWarning.severity === 'warn' ? 'text-warning' : 'text-primary'
              }`}>
                {tagWarning.severity === 'warn' ? 'Test Scenario Warning' : 'Tag Information'}
              </h4>
              <p className="text-sm text-dark-text">{tagWarning.message}</p>
              {tagWarning.tagContext && (
                <p className="text-xs text-dark-text-muted mt-2">
                  Tag context: {tagWarning.tagContext}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Metadata - Moved to top for quick reference */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Run Information</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="flex flex-col">
            <span className="text-dark-text-muted mb-1">Project</span>
            <span className="text-dark-text font-medium">{event.project}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-dark-text-muted mb-1">Provider</span>
            <span className="text-dark-text font-medium">{event.backend.provider}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-dark-text-muted mb-1">Backend</span>
            <span className="text-dark-text font-medium">{event.backend.name}</span>
          </div>
          <div className="flex flex-col">
            <span className="text-dark-text-muted mb-1">Status</span>
            <span className={`font-medium ${
              event.execution.status === 'success'
                ? 'text-success'
                : event.execution.status === 'failed'
                ? 'text-error'
                : 'text-dark-text-muted'
            }`}>
              {event.execution.status}
            </span>
          </div>
        </div>
        
        {/* SDK and Software Information */}
        {(event.software?.sdk || event.software?.python_version) && (
          <div className="mt-4 pt-4 border-t border-dark-border">
            <h4 className="text-sm font-semibold text-white mb-3">Software Environment</h4>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
              {event.software.sdk?.name && (
                <div className="flex flex-col">
                  <span className="text-dark-text-muted mb-1">SDK</span>
                  <span className="text-dark-text font-medium">
                    {event.software.sdk.name}
                    {event.software.sdk.version && (
                      <span className="text-dark-text-muted ml-1">v{event.software.sdk.version}</span>
                    )}
                  </span>
                </div>
              )}
              {event.software.python_version && (
                <div className="flex flex-col">
                  <span className="text-dark-text-muted mb-1">Python</span>
                  <span className="text-dark-text font-medium">{event.software.python_version}</span>
                </div>
              )}
              {event.software.agent_version && (
                <div className="flex flex-col">
                  <span className="text-dark-text-muted mb-1">QObserva Agent</span>
                  <span className="text-dark-text font-medium">v{event.software.agent_version}</span>
                </div>
              )}
            </div>
          </div>
        )}
        
        {event.event_id && (
          <div className="mt-4 pt-4 border-t border-dark-border">
            <div className="flex flex-col">
              <span className="text-dark-text-muted text-sm mb-1">Event ID</span>
              <span className="text-dark-text font-mono text-xs">{event.event_id}</span>
            </div>
          </div>
        )}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-6">
        {metrics['qc.quality.success_probability'] !== undefined ? (
          <MetricCard 
            label="Success Rate" 
            value={`${(metrics['qc.quality.success_probability'] * 100).toFixed(1)}%`} 
          />
        ) : metrics['qc.optimization.energy'] !== undefined ? (
          <MetricCard 
            label="Energy" 
            value={metrics['qc.optimization.energy'].toFixed(4)} 
          />
        ) : (
          <MetricCard label="Success Rate" value="N/A" />
        )}
        <MetricCard label="Shots" value={event.execution.shots.toLocaleString()} />
        <MetricCard 
          label="Runtime" 
          value={event.execution.runtime_ms 
            ? `${event.execution.runtime_ms}ms` 
            : 'N/A'} 
        />
        <MetricCard 
          label="Cost" 
          value={metrics['qc.cost.estimated_usd'] 
            ? `$${metrics['qc.cost.estimated_usd'].toFixed(4)}` 
            : 'N/A'} 
        />
      </div>
      
      {/* Energy Metrics (for D-Wave/optimization problems) */}
      {metrics['qc.optimization.energy'] !== undefined && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Optimization Results</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
            <div className="flex flex-col">
              <span className="text-dark-text-muted mb-1">Energy</span>
              <span className="text-dark-text font-medium text-lg">
                {metrics['qc.optimization.energy'].toFixed(6)}
              </span>
            </div>
            {metrics['qc.optimization.energy_stderr'] !== undefined && (
              <div className="flex flex-col">
                <span className="text-dark-text-muted mb-1">Energy Std Error</span>
                <span className="text-dark-text font-medium">
                  {metrics['qc.optimization.energy_stderr'].toFixed(6)}
                </span>
              </div>
            )}
            {metrics['qc.optimization.approximation_ratio'] !== undefined && (
              <div className="flex flex-col">
                <span className="text-dark-text-muted mb-1">Approximation Ratio</span>
                <span className={`font-medium ${
                  metrics['qc.optimization.approximation_ratio'] <= 1.1 
                    ? 'text-success' 
                    : metrics['qc.optimization.approximation_ratio'] <= 2.0
                    ? 'text-warning'
                    : 'text-error'
                }`}>
                  {metrics['qc.optimization.approximation_ratio'].toFixed(4)}x
                </span>
                <span className="text-xs text-dark-text-muted mt-1">
                  {metrics['qc.optimization.approximation_ratio'] <= 1.1 
                    ? 'Excellent (near ground state)' 
                    : metrics['qc.optimization.approximation_ratio'] <= 2.0
                    ? 'Good'
                    : 'Needs improvement'}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-2 text-white">Measurement Results</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Distribution of measurement outcomes (bitstrings) and how many times each was observed. Shows the top 20 most frequent outcomes.
          </p>
          <CountsChart counts={event.artifacts?.counts?.histogram || {}} />
        </div>
        
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Execution Timeline</h3>
          <TimelineChart 
            queueTime={event.execution.queue_ms}
            runtime={event.execution.runtime_ms}
          />
        </div>
      </div>

      {/* New Metrics Sections */}
      
      {/* Top-K Dominance */}
      {runMetrics.top1Probability !== undefined && (
        <TopKDominance 
          top1={runMetrics.top1Probability}
          top5={runMetrics.top5Probability || 0}
          top10={runMetrics.top10Probability || 0}
        />
      )}
      
      {/* Effective Support Size */}
      {runMetrics.effectiveSupportSize !== undefined && (
        <EffectiveSupport 
          effectiveSupportSize={runMetrics.effectiveSupportSize}
          totalStates={totalStates}
        />
      )}
      
      {/* Entropy Metrics */}
      {entropy !== undefined && entropy !== null && (
        <EntropyMetrics 
          entropy={entropy}
          idealEntropy={runMetrics.idealEntropy}
          entropyRatio={runMetrics.entropyRatio}
        />
      )}
      
      {/* Shot Efficiency */}
      {runMetrics.uniqueStates !== undefined && event.execution?.shots && (
        <ShotEfficiency 
          uniqueStates={runMetrics.uniqueStates}
          shots={event.execution.shots}
          uniqueStatesRatio={runMetrics.uniqueStatesRatio || 0}
          collisionRate={runMetrics.collisionRate || 0}
        />
      )}
      
      {/* Runtime Metrics */}
      {runMetrics.runtimePerShot !== undefined && event.execution?.runtime_ms !== undefined && (
        <RuntimeMetrics 
          runtimeMs={event.execution.runtime_ms || 0}
          queueMs={event.execution.queue_ms || 0}
          shots={event.execution.shots || 0}
          runtimePerShot={runMetrics.runtimePerShot}
          classification={runMetrics.runtimeClassification || 'unknown'}
        />
      )}

      {/* Execution time breakdown (CPU / QPU / queue / post-processing) when provided by backend */}
      {(metrics['qc.time.cpu_s'] != null || metrics['qc.time.qpu_s'] != null ||
        metrics['qc.time.queue_s'] != null || metrics['qc.time.post_processing_s'] != null) && (
        <ExecutionTimeBreakdown
          cpuTimeS={metrics['qc.time.cpu_s']}
          qpuTimeS={metrics['qc.time.qpu_s']}
          queueTimeS={metrics['qc.time.queue_s']}
          postProcessingTimeS={metrics['qc.time.post_processing_s']}
        />
      )}

      {/* Detailed Metadata (Expandable) */}
      <div className="card">
        <button
          onClick={() => toggleSection('rawMetadata')}
          className="w-full flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-white">Detailed Metadata</h3>
          {expandedSections.rawMetadata ? (
            <ChevronUp className="text-dark-text-muted" />
          ) : (
            <ChevronDown className="text-dark-text-muted" />
          )}
        </button>
        
        {expandedSections.rawMetadata && (
          <div className="mt-4 space-y-4">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="flex justify-between">
                <span className="text-dark-text-muted">Run ID:</span>
                <span className="text-dark-text font-mono text-xs">{event.run_id}</span>
              </div>
              {event.event_id && (
                <div className="flex justify-between">
                  <span className="text-dark-text-muted">Event ID:</span>
                  <span className="text-dark-text font-mono text-xs">{event.event_id}</span>
                </div>
              )}
              {event.created_at && (
                <div className="flex justify-between">
                  <span className="text-dark-text-muted">Created At:</span>
                  <span className="text-dark-text">{new Date(event.created_at).toLocaleString()}</span>
                </div>
              )}
            </div>
            
            {/* Raw Metadata JSON */}
            <div className="mt-4">
              <h4 className="text-sm font-semibold text-dark-text-muted mb-2">Raw Metadata (JSON)</h4>
              <pre className="bg-dark-bg border border-dark-border rounded-lg p-4 text-xs text-dark-text overflow-auto max-h-96">
                {JSON.stringify({
                  project: event.project,
                  backend: event.backend,
                  run_id: event.run_id,
                  event_id: event.event_id || undefined,
                  created_at: event.created_at || undefined,
                  execution: {
                    status: event.execution.status,
                    shots: event.execution.shots,
                    runtime_ms: event.execution.runtime_ms,
                    queue_ms: event.execution.queue_ms,
                  },
                }, null, 2)}
              </pre>
            </div>
          </div>
        )}
      </div>

      {/* Insights */}
      {analysis.insights && analysis.insights.length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Insights</h3>
          <div className="space-y-2">
            {analysis.insights.map((insight, idx) => (
              <div
                key={idx}
                className={`p-3 rounded-lg ${
                  insight.severity === 'critical'
                    ? 'bg-error/20 border border-error/30 text-error'
                    : insight.severity === 'warn'
                    ? 'bg-warning/20 border border-warning/30 text-warning'
                    : 'bg-primary/20 border border-primary/30 text-primary'
                }`}
              >
                {insight.summary}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Artifacts Debug (for D-Wave/optimization) */}
      {event.artifacts?.energies && (
        <div className="card border-l-4 border-primary">
          <h3 className="text-lg font-semibold mb-2 text-white">Energy Artifacts (Debug)</h3>
          <div className="text-sm">
            <div className="mb-2">
              <span className="text-dark-text-muted">Energy Value:</span>
              <span className="text-dark-text font-mono ml-2">
                {event.artifacts.energies?.value !== null && event.artifacts.energies?.value !== undefined
                  ? String(event.artifacts.energies.value)
                  : 'null/undefined'}
              </span>
            </div>
            <div className="mb-2">
              <span className="text-dark-text-muted">Energy Std Error:</span>
              <span className="text-dark-text font-mono ml-2">
                {event.artifacts.energies?.stderr !== null && event.artifacts.energies?.stderr !== undefined
                  ? String(event.artifacts.energies.stderr)
                  : 'null/undefined'}
              </span>
            </div>
            <div className="text-xs text-dark-text-muted mt-2">
              If energy value is null/undefined, the adapter didn't extract it. 
              If it has a value but metrics don't show it, the analysis needs to be re-run.
            </div>
          </div>
        </div>
      )}

      {/* Raw Event Data */}
      <div className="card">
        <button
          onClick={() => toggleSection('rawEvent')}
          className="w-full flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-white">Raw Event Data</h3>
          {expandedSections.rawEvent ? (
            <ChevronUp className="text-dark-text-muted" />
          ) : (
            <ChevronDown className="text-dark-text-muted" />
          )}
        </button>
        {expandedSections.rawEvent && (
          <div className="mt-4">
            <pre className="bg-dark-bg border border-dark-border rounded-lg p-4 text-xs text-dark-text overflow-auto max-h-96">
              {JSON.stringify(event, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* Raw Analytics Data */}
      <div className="card">
        <button
          onClick={() => toggleSection('rawAnalysis')}
          className="w-full flex items-center justify-between text-left"
        >
          <h3 className="text-lg font-semibold text-white">Raw Analytics Data</h3>
          {expandedSections.rawAnalysis ? (
            <ChevronUp className="text-dark-text-muted" />
          ) : (
            <ChevronDown className="text-dark-text-muted" />
          )}
        </button>
        {expandedSections.rawAnalysis && (
          <div className="mt-4">
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-dark-text-muted mb-2">Metrics</h4>
              <pre className="bg-dark-bg border border-dark-border rounded-lg p-4 text-xs text-dark-text overflow-auto max-h-64">
                {JSON.stringify(metrics, null, 2)}
              </pre>
            </div>
            {analysis.insights && analysis.insights.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold text-dark-text-muted mb-2">Insights</h4>
                <pre className="bg-dark-bg border border-dark-border rounded-lg p-4 text-xs text-dark-text overflow-auto max-h-64">
                  {JSON.stringify(analysis.insights, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
