import MetricCard from '../MetricCard';

interface Props {
  cpuTimeS?: number | null;
  qpuTimeS?: number | null;
  queueTimeS?: number | null;
  postProcessingTimeS?: number | null;
}

export default function ExecutionTimeBreakdown({
  cpuTimeS,
  qpuTimeS,
  queueTimeS,
  postProcessingTimeS,
}: Props) {
  const format = (v: number) => `${v.toFixed(2)} s`;
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Execution time breakdown</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Provider-reported time spent in CPU, QPU, queue, and post-processing. Shown when the backend supplies this metadata (e.g. IBM cloud/hardware).
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cpuTimeS != null && (
          <MetricCard label="CPU" value={format(cpuTimeS)} />
        )}
        {qpuTimeS != null && (
          <MetricCard label="QPU" value={format(qpuTimeS)} />
        )}
        {queueTimeS != null && (
          <MetricCard label="Queue (provider)" value={format(queueTimeS)} />
        )}
        {postProcessingTimeS != null && (
          <MetricCard label="Post-processing" value={format(postProcessingTimeS)} />
        )}
      </div>
    </div>
  );
}
