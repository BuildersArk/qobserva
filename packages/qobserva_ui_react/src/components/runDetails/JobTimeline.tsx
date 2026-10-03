import MetricCard from '../MetricCard';
import type { Event } from '../../services/api';

interface Props {
  execution: Event['execution'];
}

const SOURCE_TEXT: Record<string, string> = {
  ibm_runtime_job: 'IBM Runtime job',
  braket_task: 'Braket task',
};

function toDate(v?: string): Date | null {
  if (!v) return null;
  const d = new Date(v);
  return Number.isNaN(d.getTime()) ? null : d;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${Math.round(ms)} ms`;
  if (ms < 120000) return `${(ms / 1000).toFixed(2)} s`;
  return `${(ms / 60000).toFixed(1)} min`;
}

export default function JobTimeline({ execution }: Props) {
  const tl = execution.timeline || {};
  const created = toDate(tl.created);
  const running = toDate(tl.running);
  const finished = toDate(tl.finished);
  const spans = execution.execution_spans;
  const chunks = execution.chunk_timing;

  // QPU execution as bars on one time axis: executor chunks (with their items), or execution spans.
  const bars: Array<{ label: string; start: number; stop: number; detail?: string }> = [];
  (chunks?.chunks || []).forEach((c, i) => {
    const s0 = toDate(c.start), s1 = toDate(c.stop);
    if (s0 && s1) {
      const parts = (c.parts || []).map((p) => `item ${p.item} × ${p.size}`).join(', ');
      bars.push({ label: `Chunk ${i}`, start: s0.getTime(), stop: s1.getTime(), detail: parts });
    }
  });
  if (bars.length === 0) {
    (spans?.spans || []).forEach((sp, i) => {
      const s0 = toDate(sp.start), s1 = toDate(sp.stop);
      if (s0 && s1) bars.push({ label: `Span ${i}`, start: s0.getTime(), stop: s1.getTime() });
    });
  }
  const t0 = bars.length ? Math.min(...bars.map((b) => b.start)) : 0;
  const tEnd = bars.length ? Math.max(...bars.map((b) => b.stop)) : 0;
  const width = Math.max(tEnd - t0, 1);

  const steps: Array<[string, Date | null]> = [
    ['Created', created],
    ['Running', running],
    ['Finished', finished],
  ];

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Job Timeline</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Timestamps reported by the provider{tl.source && SOURCE_TEXT[tl.source] ? ` for this ${SOURCE_TEXT[tl.source]}` : ''}
        {chunks ? ', and the QPU chunk timing' : spans ? ', and the QPU execution spans' : ''}. Times are shown in your local time zone.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {created && running && (
          <MetricCard label="Waiting (queue)" value={formatDuration(running.getTime() - created.getTime())} />
        )}
        {running && finished && (
          <MetricCard label="Running" value={formatDuration(finished.getTime() - running.getTime())} />
        )}
        {created && finished && (
          <MetricCard label="Total" value={formatDuration(finished.getTime() - created.getTime())} />
        )}
        {chunks ? (
          <MetricCard label={`QPU Chunks (${chunks.count})`} value={formatDuration(chunks.total_s * 1000)} />
        ) : spans ? (
          <MetricCard label={`QPU Spans (${spans.count})`} value={formatDuration(spans.total_s * 1000)} />
        ) : null}
      </div>
      <div className="mt-4 space-y-1 text-sm">
        {steps.filter(([, d]) => d).map(([label, d]) => (
          <div key={label} className="flex justify-between">
            <span className="text-dark-text-muted">{label}</span>
            <span className="text-dark-text font-mono text-xs">{d!.toLocaleString()}</span>
          </div>
        ))}
      </div>
      {bars.length > 0 && (
        <div className="mt-6">
          <span className="text-sm text-dark-text-muted">
            {chunks ? 'Chunk timing and composition' : 'QPU execution spans'} ({formatDuration(width)} from first start to last stop)
          </span>
          <div className="mt-2 space-y-2">
            {bars.map((b) => (
              <div key={b.label} className="flex items-center gap-3 text-xs">
                <span className="w-16 text-dark-text-muted">{b.label}</span>
                <div className="flex-1 h-4 bg-dark-bg rounded relative overflow-hidden">
                  <div
                    className="absolute h-4 bg-primary rounded"
                    style={{ left: `${((b.start - t0) / width) * 100}%`, width: `${Math.max(((b.stop - b.start) / width) * 100, 0.5)}%` }}
                    title={`${formatDuration(b.stop - b.start)}${b.detail ? ` · ${b.detail}` : ''}`}
                  />
                </div>
                <span className="w-40 text-right text-dark-text font-mono">
                  {formatDuration(b.stop - b.start)}{b.detail ? ` · ${b.detail}` : ''}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
