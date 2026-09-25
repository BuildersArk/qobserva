import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { Run } from '../../services/api';
import { format, parseISO, startOfDay } from 'date-fns';

interface Props {
  runs: Run[];
  baseFilters?: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
  };
}

function toQuery(base?: Props['baseFilters'], extra?: Record<string, string | undefined>) {
  const params = new URLSearchParams();
  const merged = { ...(base || {}), ...(extra || {}) };
  Object.entries(merged).forEach(([k, v]) => {
    if (v) params.set(k, v);
  });
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export default function RuntimeTrend({ runs, baseFilters }: Props) {
  const navigate = useNavigate();
  // Runtime comes with the run list (include_summary) for a sample of the latest 50 runs
  const data = useMemo(() => {
    // Group by date and calculate average runtime
    const grouped = new Map<string, { total: number; count: number }>();
    
    runs.slice(0, 50).forEach((run) => {
      const detail = { created_at: run.created_at, runtime_ms: run.summary?.runtime_ms || 0 };
      const date = format(startOfDay(parseISO(detail.created_at)), 'yyyy-MM-dd');
      
      if (!grouped.has(date)) {
        grouped.set(date, { total: 0, count: 0 });
      }
      
      const stats = grouped.get(date)!;
      stats.total += detail.runtime_ms || 0;
      stats.count += 1;
    });
    
    return Array.from(grouped.entries())
      .map(([date, stats]) => ({
        dateLabel: format(parseISO(date), 'MMM dd'),
        dateIso: date, // yyyy-MM-dd
        avgRuntime: stats.count > 0 ? stats.total / stats.count : 0,
      }))
      .sort((a, b) => a.dateIso.localeCompare(b.dateIso));
  }, [runs]);

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No runtime data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <AreaChart
        data={data}
        onClick={(state: any) => {
          const payload = state?.activePayload;
          if (!payload || payload.length === 0) return;
          const dateIso = payload[0]?.payload?.dateIso; // yyyy-MM-dd
          if (!dateIso) return;
          navigate(`/runs-filtered${toQuery(baseFilters, {
            startDate: `${dateIso}T00:00:00Z`,
            endDate: `${dateIso}T23:59:59Z`,
          })}`);
        }}
      >
        <defs>
          <linearGradient id="colorRuntime" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1}/>
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="dateLabel"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          label={{ value: 'Avg Runtime (ms)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#e2e8f0',
          }}
          labelStyle={{ color: '#e2e8f0' }}
          itemStyle={{ color: '#e2e8f0' }}
          formatter={(value: number) => [`${value.toFixed(0)} ms`, 'Average Runtime']}
        />
        <Legend wrapperStyle={{ color: '#e2e8f0' }} />
        <Area
          type="monotone"
          dataKey="avgRuntime"
          stroke="#3b82f6"
          strokeWidth={2}
          fillOpacity={1}
          fill="url(#colorRuntime)"
          style={{ cursor: 'pointer' }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
