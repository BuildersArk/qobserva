import { useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { apiService, Run } from '../services/api';
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts';

type ReportType = 'home' | 'analytics' | 'executive' | 'provider_backend' | 'quality_anomaly';

function parseFilters(searchParams: URLSearchParams) {
  const project = searchParams.get('project') || undefined;
  const startDate = searchParams.get('startDate') || undefined;
  const endDate = searchParams.get('endDate') || undefined;
  return { project, startDate, endDate };
}

function formatIso(iso?: string) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function groupCount(runs: Run[], keyFn: (r: Run) => string) {
  const m = new Map<string, number>();
  runs.forEach((r) => {
    const k = keyFn(r) || 'unknown';
    m.set(k, (m.get(k) || 0) + 1);
  });
  return Array.from(m.entries()).sort((a, b) => b[1] - a[1]);
}

const PALETTE = {
  blue: '#2563eb',
  green: '#10b981',
  red: '#ef4444',
  amber: '#f59e0b',
  violet: '#8b5cf6',
  slate: '#64748b',
};

function pct(part: number, total: number) {
  if (!total) return '0%';
  return `${Math.round((part / total) * 100)}%`;
}

function PieLegend({ items, total }: { items: Array<{ name: string; value: number; color: string }>; total: number }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 6, marginTop: 8 }}>
      {items.map((it) => (
        <div key={it.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ width: 10, height: 10, borderRadius: 999, background: it.color, display: 'inline-block' }} />
            <span style={{ color: '#111827', textTransform: 'capitalize' }}>{it.name}</span>
          </div>
          <div style={{ color: '#111827' }}>
            <span style={{ fontWeight: 800 }}>{it.value.toLocaleString()}</span> <span style={{ color: '#6b7280' }}>({pct(it.value, total)})</span>
          </div>
        </div>
      ))}
    </div>
  );
}

function Card({ title, children }: { title: string; children: any }) {
  return (
    <div style={{ border: '1px solid #e5e7eb', borderRadius: 12, padding: 12, background: 'white' }}>
      <div style={{ fontSize: 13, fontWeight: 800, color: '#111827', marginBottom: 10 }}>{title}</div>
      {children}
    </div>
  );
}

export default function ReportPrint() {
  const [searchParams] = useSearchParams();
  const type = (searchParams.get('type') || 'executive') as ReportType;
  const filters = useMemo(() => parseFilters(searchParams), [searchParams]);

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs-report', type, filters],
    queryFn: () =>
      apiService.getRuns({
        limit: 10000,
        project: filters.project,
        startDate: filters.startDate,
        endDate: filters.endDate,
      }),
    staleTime: 0,
  });

  useEffect(() => {
    // Auto-open print dialog for PDF export. If a browser blocks this,
    // user can still use Ctrl/Cmd+P.
    const t = setTimeout(() => {
      try {
        window.print();
      } catch {
        // ignore
      }
    }, 300);
    return () => clearTimeout(t);
  }, []);

  const totals = useMemo(() => {
    const total = runs.length;
    const success = runs.filter((r) => r.status === 'success').length;
    const failed = runs.filter((r) => r.status === 'failed').length;
    const cancelled = runs.filter((r) => r.status === 'cancelled').length;
    const shots = runs.reduce((s, r) => s + (r.shots || 0), 0);
    return { total, success, failed, cancelled, shots };
  }, [runs]);

  const byProject = useMemo(() => groupCount(runs, (r) => r.project), [runs]);
  const byProvider = useMemo(() => groupCount(runs, (r) => r.provider), [runs]);
  const byBackend = useMemo(() => groupCount(runs, (r) => r.backend_name), [runs]);

  const providerPie = useMemo(() => {
    const top = byProvider.slice(0, 6);
    const used = top.reduce((s, [, v]) => s + v, 0);
    const other = Math.max(totals.total - used, 0);
    const colors = [PALETTE.blue, PALETTE.violet, PALETTE.green, PALETTE.amber, PALETTE.red, PALETTE.slate];
    const items = top.map(([name, value], idx) => ({ name, value, color: colors[idx % colors.length] }));
    if (other > 0) items.push({ name: 'other', value: other, color: '#9ca3af' });
    return items.filter((d) => d.value > 0);
  }, [byProvider, totals.total]);

  const statusPie = useMemo(() => {
    const success = totals.success;
    const failed = totals.failed;
    const cancelled = totals.cancelled;
    const other = Math.max(totals.total - success - failed - cancelled, 0);
    return [
      { name: 'success', value: success, color: PALETTE.green },
      { name: 'failed', value: failed, color: PALETTE.red },
      { name: 'cancelled', value: cancelled, color: PALETTE.slate },
      ...(other ? [{ name: 'other', value: other, color: PALETTE.amber }] : []),
    ].filter((d) => d.value > 0);
  }, [totals]);

  const shotsBuckets = useMemo(() => {
    const buckets = [
      { label: '0-10', min: 0, max: 10, value: 0 },
      { label: '11-100', min: 11, max: 100, value: 0 },
      { label: '101-1K', min: 101, max: 1000, value: 0 },
      { label: '1K-10K', min: 1001, max: 10000, value: 0 },
      { label: '10K+', min: 10001, max: Number.POSITIVE_INFINITY, value: 0 },
    ];
    runs.forEach((r) => {
      const s = r.shots || 0;
      const b = buckets.find((x) => s >= x.min && s <= x.max);
      if (b) b.value += 1;
    });
    return buckets.filter((b) => b.value > 0);
  }, [runs]);

  const runsOverTime = useMemo(() => {
    const m = new Map<string, { date: string; runs: number }>();
    runs.forEach((r) => {
      const d = new Date(r.created_at);
      const key = `${d.getUTCFullYear()}-${String(d.getUTCMonth() + 1).padStart(2, '0')}-${String(d.getUTCDate()).padStart(2, '0')}`;
      if (!m.has(key)) m.set(key, { date: key, runs: 0 });
      m.get(key)!.runs += 1;
    });
    return Array.from(m.values())
      .sort((a, b) => a.date.localeCompare(b.date))
      .map((x) => ({ ...x, label: x.date.slice(5) })); // MM-DD
  }, [runs]);

  const anomalyRuns = useMemo(() => {
    const unknown = (r: Run) => r.provider === 'unknown' || r.backend_name === 'unknown';
    const lowShots = (r: Run) => (r.shots || 0) <= 10;
    const failed = (r: Run) => r.status === 'failed';
    return runs
      .filter((r) => unknown(r) || lowShots(r) || failed(r))
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 40);
  }, [runs]);

  const title =
    type === 'home'
      ? 'Home Dashboard Export'
      : type === 'analytics'
      ? 'Run Analytics Dashboard Export'
      : type === 'executive'
      ? 'Executive Summary Report'
      : type === 'provider_backend'
      ? 'Provider/Backend Performance Report'
      : 'Run Quality / Anomaly Report';

  return (
    <div style={{ padding: 24, fontFamily: 'system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif' }}>
      <style>{`
        @media print {
          @page { margin: 12mm; }
          .no-print { display: none !important; }
          .page-break { break-before: page; }
        }
        table { width: 100%; border-collapse: collapse; }
        th, td { border-bottom: 1px solid #e5e7eb; padding: 8px 6px; text-align: left; font-size: 12px; }
        th { font-size: 12px; color: #111827; }
        .muted { color: #6b7280; }
        .kpi { border: 1px solid #e5e7eb; border-radius: 12px; padding: 10px; background: white; }
        .kpi-title { font-size: 12px; color: #6b7280; margin-bottom: 4px; }
        .kpi-val { font-size: 18px; font-weight: 700; color: #111827; }
      `}</style>

      <div className="no-print" style={{ marginBottom: 12, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="muted" style={{ fontSize: 12 }}>
          Tip: Use browser “Save as PDF”. If the print dialog didn’t open, press Ctrl+P.
        </div>
        <button onClick={() => window.print()} style={{ padding: '8px 12px', border: '1px solid #e5e7eb', borderRadius: 8, background: 'white' }}>
          Print / Save PDF
        </button>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: 12 }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 800, color: '#111827' }}>{title}</div>
          <div className="muted" style={{ fontSize: 12, marginTop: 4 }}>
            Generated: {new Date().toLocaleString()}
          </div>
        </div>
        <div className="muted" style={{ fontSize: 12, textAlign: 'right' }}>
          <div>Project: {filters.project || 'All'}</div>
          <div>Start: {formatIso(filters.startDate)}</div>
          <div>End: {formatIso(filters.endDate)}</div>
        </div>
      </div>
      <div style={{ height: 4, borderRadius: 999, background: 'linear-gradient(90deg, #2563eb, #8b5cf6, #10b981)', marginTop: 10 }} />

      {isLoading ? (
        <div style={{ marginTop: 24 }} className="muted">
          Loading report data…
        </div>
      ) : (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10, marginTop: 18 }}>
            <div className="kpi">
              <div className="kpi-title">Total Runs</div>
              <div className="kpi-val">{totals.total.toLocaleString()}</div>
            </div>
            <div className="kpi">
              <div className="kpi-title">Success</div>
              <div className="kpi-val">{totals.success.toLocaleString()}</div>
            </div>
            <div className="kpi">
              <div className="kpi-title">Failed</div>
              <div className="kpi-val">{totals.failed.toLocaleString()}</div>
            </div>
            <div className="kpi">
              <div className="kpi-title">Cancelled</div>
              <div className="kpi-val">{totals.cancelled.toLocaleString()}</div>
            </div>
            <div className="kpi">
              <div className="kpi-title">Total Shots</div>
              <div className="kpi-val">{totals.shots.toLocaleString()}</div>
            </div>
          </div>

          {/* Executive Summary / Dashboard-style exports */}
          {(type === 'executive' || type === 'home' || type === 'analytics') && (
            <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: 14 }}>
              <Card title="Run Volume Over Time">
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={runsOverTime}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="label" tick={{ fill: '#374151', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#374151', fontSize: 11 }} />
                      <Tooltip />
                      <Line type="monotone" dataKey="runs" stroke={PALETTE.blue} strokeWidth={2} dot={{ r: 2 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="Status Distribution">
                <div style={{ width: '100%', height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusPie}
                        dataKey="value"
                        nameKey="name"
                        innerRadius={48}
                        outerRadius={78}
                        labelLine={false}
                        label={({ name, percent }: any) => `${String(name)} ${(percent * 100).toFixed(0)}%`}
                      >
                        {statusPie.map((s) => (
                          <Cell key={s.name} fill={s.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <PieLegend items={statusPie} total={totals.total} />
              </Card>
            </div>
          )}

          {/* Provider/Backend Performance */}
          {type === 'provider_backend' && (
            <div style={{ marginTop: 18, display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
              <Card title="Top Providers (by run count)">
                <table>
                  <thead>
                    <tr>
                      <th>Provider</th>
                      <th>Runs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byProvider.slice(0, 12).map(([k, v]) => (
                      <tr key={k}>
                        <td>{k}</td>
                        <td>{v.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
              <Card title="Top Backends (by run count)">
                <table>
                  <thead>
                    <tr>
                      <th>Backend</th>
                      <th>Runs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byBackend.slice(0, 12).map(([k, v]) => (
                      <tr key={k}>
                        <td>{k}</td>
                        <td>{v.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
              <Card title="Provider Share (donut)">
                <div style={{ width: '100%', height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={providerPie} dataKey="value" nameKey="name" innerRadius={48} outerRadius={78} labelLine={false}>
                        {providerPie.map((s) => (
                          <Cell key={s.name} fill={s.color} />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <PieLegend items={providerPie} total={totals.total} />
              </Card>
              <Card title="Shots Distribution (buckets)">
                <div style={{ width: '100%', height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={shotsBuckets}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                      <XAxis dataKey="label" tick={{ fill: '#374151', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#374151', fontSize: 11 }} />
                      <Tooltip />
                      <Bar dataKey="value" fill={PALETTE.violet} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </Card>
              <Card title="Projects (by run count)">
                <table>
                  <thead>
                    <tr>
                      <th>Project</th>
                      <th>Runs</th>
                    </tr>
                  </thead>
                  <tbody>
                    {byProject.slice(0, 12).map(([k, v]) => (
                      <tr key={k}>
                        <td>{k}</td>
                        <td>{v.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            </div>
          )}

          {/* Quality / Anomaly */}
          {type === 'quality_anomaly' && (
            <div style={{ marginTop: 18 }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
                <Card title="Anomaly Counters">
                  <div style={{ fontSize: 12, color: '#111827', lineHeight: 1.6 }}>
                    <div>
                      <span style={{ fontWeight: 800, color: PALETTE.amber }}>
                        {runs.filter((r) => r.provider === 'unknown' || r.backend_name === 'unknown').length.toLocaleString()}
                      </span>{' '}
                      runs with unknown provider/backend
                    </div>
                    <div>
                      <span style={{ fontWeight: 800, color: PALETTE.violet }}>
                        {runs.filter((r) => (r.shots || 0) <= 10).length.toLocaleString()}
                      </span>{' '}
                      low-shot runs (≤ 10)
                    </div>
                    <div>
                      <span style={{ fontWeight: 800, color: PALETTE.red }}>{totals.failed.toLocaleString()}</span> failed runs
                    </div>
                  </div>
                  <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
                    The table below lists a sample of runs that match these conditions.
                  </div>
                </Card>
                <Card title="Status Distribution">
                  <div style={{ width: '100%', height: 200 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={statusPie}
                          dataKey="value"
                          nameKey="name"
                          innerRadius={48}
                          outerRadius={78}
                          labelLine={false}
                          label={({ name, percent }: any) => `${String(name)} ${(percent * 100).toFixed(0)}%`}
                        >
                          {statusPie.map((s) => (
                            <Cell key={s.name} fill={s.color} />
                          ))}
                        </Pie>
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <PieLegend items={statusPie} total={totals.total} />
                </Card>
              </div>
              <div style={{ marginTop: 14 }}>
                <Card title="Anomalous Runs (sample)">
                  <table>
                    <thead>
                      <tr>
                        <th>Run ID</th>
                        <th>Time</th>
                        <th>Project</th>
                        <th>Provider</th>
                        <th>Backend</th>
                        <th>Status</th>
                        <th>Shots</th>
                      </tr>
                    </thead>
                    <tbody>
                      {anomalyRuns.map((r) => (
                        <tr key={r.run_id}>
                          <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>{r.run_id}</td>
                          <td>{new Date(r.created_at).toLocaleString()}</td>
                          <td>{r.project}</td>
                          <td style={{ color: r.provider === 'unknown' ? PALETTE.amber : '#111827' }}>{r.provider}</td>
                          <td style={{ color: r.backend_name === 'unknown' ? PALETTE.amber : '#111827' }}>{r.backend_name}</td>
                          <td style={{ color: r.status === 'failed' ? PALETTE.red : '#111827' }}>{r.status}</td>
                          <td style={{ color: (r.shots || 0) <= 10 ? PALETTE.violet : '#111827' }}>{(r.shots || 0).toLocaleString()}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </Card>
              </div>
            </div>
          )}

          {/* Footer-ish: short recent runs table for all report types */}
          <div className="page-break" style={{ marginTop: 22 }}>
            <Card title="Recent Runs (sample)">
              <table>
                <thead>
                  <tr>
                    <th>Run ID</th>
                    <th>Time</th>
                    <th>Project</th>
                    <th>Provider</th>
                    <th>Backend</th>
                    <th>Status</th>
                    <th>Shots</th>
                  </tr>
                </thead>
                <tbody>
                  {runs
                    .slice()
                    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
                    .slice(0, 35)
                    .map((r) => (
                      <tr key={r.run_id}>
                        <td style={{ fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace' }}>{r.run_id}</td>
                        <td>{new Date(r.created_at).toLocaleString()}</td>
                        <td>{r.project}</td>
                        <td>{r.provider}</td>
                        <td>{r.backend_name}</td>
                        <td>{r.status}</td>
                        <td>{(r.shots || 0).toLocaleString()}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

