import type { ExpectationArtifact } from '../../services/api';

interface Props {
  expectations: ExpectationArtifact[];
}

const MAX_ROWS = 50;

function formatNumber(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '—';
  return Math.abs(v) >= 1e-4 || v === 0 ? v.toFixed(6) : v.toExponential(3);
}

export default function ExpectationValues({ expectations }: Props) {
  const rows = expectations.slice(0, MAX_ROWS);
  const hasStderr = rows.some((e) => e.stderr !== null && e.stderr !== undefined);
  const hasKind = rows.some((e) => e.kind && e.kind !== 'expectation');

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Expectation Values</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Observable values returned by the run (e.g. Estimator results, <span className="font-mono">expval</span> measurements).
        Labels are the observable when the SDK reports it, otherwise the position in the result.
      </p>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-dark-border">
              <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Observable</th>
              {hasKind && (
                <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Type</th>
              )}
              <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Value</th>
              {hasStderr && (
                <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Std Error</th>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((e, i) => (
              <tr key={`${e.operator}-${i}`} className="border-b border-dark-border">
                <td className="py-3 px-4 text-sm text-dark-text font-mono">{e.operator}</td>
                {hasKind && (
                  <td className="py-3 px-4 text-sm text-dark-text">{e.kind || 'expectation'}</td>
                )}
                <td className="py-3 px-4 text-sm text-dark-text text-right font-medium">{formatNumber(e.value)}</td>
                {hasStderr && (
                  <td className="py-3 px-4 text-sm text-dark-text-muted text-right">{formatNumber(e.stderr)}</td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {expectations.length > MAX_ROWS && (
        <p className="text-xs text-dark-text-muted mt-3">
          Showing {MAX_ROWS} of {expectations.length.toLocaleString()} values. All values are in the raw event data below.
        </p>
      )}
    </div>
  );
}
