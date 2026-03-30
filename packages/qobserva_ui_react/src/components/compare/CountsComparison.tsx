import { Event } from '../../services/api';
import CountsChart from '../charts/CountsChart';

interface Props {
  runA: { event: Event; runId: string; label: string };
  runB: { event: Event; runId: string; label: string };
}

export default function CountsComparison({ runA, runB }: Props) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Measurement Results Comparison</h3>
      <div className="grid grid-cols-2 gap-6">
        <div>
          <h4 className="text-sm font-medium text-dark-text-muted mb-2">{runA.label}</h4>
          <CountsChart counts={runA.event.artifacts?.counts?.histogram || {}} />
        </div>
        <div>
          <h4 className="text-sm font-medium text-dark-text-muted mb-2">{runB.label}</h4>
          <CountsChart counts={runB.event.artifacts?.counts?.histogram || {}} />
        </div>
      </div>
    </div>
  );
}
