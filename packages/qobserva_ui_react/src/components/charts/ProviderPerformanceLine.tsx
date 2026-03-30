import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
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

export default function ProviderPerformanceLine({ runs, baseFilters }: Props) {
  const navigate = useNavigate();
  const data = useMemo(() => {
    // Group runs by date and provider, calculate average runtime
    const grouped = new Map<string, Map<string, { total: number; count: number }>>();
    
    runs.forEach(run => {
      if (!run.created_at) return;
      
      const date = format(startOfDay(parseISO(run.created_at)), 'yyyy-MM-dd');
      const provider = run.provider;
      
      if (!grouped.has(date)) {
        grouped.set(date, new Map());
      }
      
      const providers = grouped.get(date)!;
      if (!providers.has(provider)) {
        providers.set(provider, { total: 0, count: 0 });
      }
      
      const stats = providers.get(provider)!;
      // Use a placeholder for runtime if not available - in real scenario would fetch full run data
      stats.count += 1;
    });
    
    // Convert to array format for chart
    const dates = Array.from(grouped.keys()).sort();
    const providers = Array.from(new Set(runs.map(r => r.provider))).filter(Boolean);
    
    return dates.map(date => {
      const entry: any = {
        dateLabel: format(parseISO(date), 'MMM dd'),
        dateIso: date, // yyyy-MM-dd
      };
      const providersForDate = grouped.get(date);
      
      providers.forEach(provider => {
        const stats = providersForDate?.get(provider);
        if (stats && stats.count > 0) {
          // For now, show run count per provider per day
          // In production, would calculate average runtime from full run data
          entry[provider] = stats.count;
        }
      });
      
      return entry;
    });
  }, [runs]);

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  const providers = Array.from(new Set(runs.map(r => r.provider))).filter(Boolean);
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#14b8a6'];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <LineChart
        data={data}
        onClick={(state: any) => {
          // Click a dot/line segment to drill into runs for that provider on that day
          const payload = state?.activePayload;
          if (!payload || payload.length === 0) return;
          const provider = payload[0]?.dataKey;
          const dateIso = payload[0]?.payload?.dateIso; // yyyy-MM-dd
          if (!provider || !dateIso) return;
          navigate(`/runs-filtered${toQuery(baseFilters, {
            provider: String(provider),
            startDate: `${dateIso}T00:00:00Z`,
            endDate: `${dateIso}T23:59:59Z`,
          })}`);
        }}
      >
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
          label={{ value: 'Runs per Day', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#e2e8f0' }}
        />
        <Legend wrapperStyle={{ color: '#e2e8f0' }} />
        {providers.map((provider, idx) => (
          <Line
            key={provider}
            type="monotone"
            dataKey={provider}
            stroke={colors[idx % colors.length]}
            strokeWidth={2}
            dot={{ r: 4 }}
            activeDot={{ r: 6 }}
            style={{ cursor: 'pointer' }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
