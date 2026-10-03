import type { BatchArtifact } from '../../services/api';

interface Props {
  batches: BatchArtifact[];
}

const MAX_ROWS = 50;

function batchLabel(b: BatchArtifact, i: number): string {
  if (b.label) return b.label;
  const params = Object.entries(b.params || {});
  if (params.length > 0) {
    return params
      .map(([k, v]) => `${k} = ${typeof v === 'number' ? Number(v.toPrecision(6)) : v}`)
      .join(', ');
  }
  return `#${i}`;
}

function topOutcome(histogram: Record<string, number>): [string, number] | null {
  let best: [string, number] | null = null;
  for (const [k, v] of Object.entries(histogram || {})) {
    if (!best || v > best[1]) best = [k, v];
  }
  return best;
}

export default function BatchResults({ batches }: Props) {
  const rows = batches.slice(0, MAX_ROWS);

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Batch Results</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        One row per circuit execution in this run: a parameter sweep point, a shot-vector group, or a PUB.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-border">
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Execution</th>
              <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Shots</th>
              <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Distinct Outcomes</th>
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Most Frequent</th>
              <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Probability</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((b, i) => {
              const top = topOutcome(b.histogram);
              const shots = b.shots || Object.values(b.histogram || {}).reduce((a, v) => a + v, 0);
              return (
                <tr key={i} className="border-b border-dark-border">
                  <td className="py-3 px-4 text-sm text-dark-text font-mono">{batchLabel(b, i)}</td>
                  <td className="py-3 px-4 text-sm text-dark-text text-right">{shots.toLocaleString()}</td>
                  <td className="py-3 px-4 text-sm text-dark-text text-right">
                    {Object.keys(b.histogram || {}).length.toLocaleString()}
                  </td>
                  <td className="py-3 px-4 text-sm text-dark-text font-mono">{top ? top[0] : '—'}</td>
                  <td className="py-3 px-4 text-sm text-dark-text text-right font-medium">
                    {top && shots > 0 ? `${((top[1] / shots) * 100).toFixed(1)}%` : '—'}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {batches.length > MAX_ROWS && (
        <p className="text-xs text-dark-text-muted mt-3">
          Showing {MAX_ROWS} of {batches.length.toLocaleString()} executions. All results are in the raw event data below.
        </p>
      )}
    </div>
  );
}
