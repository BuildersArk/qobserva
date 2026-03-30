import { useMemo } from 'react';
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart, Legend } from 'recharts';
import { Run } from '../../services/api';

interface Props {
  runs: Run[];
}

export default function SuccessTrend({ runs }: Props) {
  const data = useMemo(() => {
    // Group by date and calculate success and failure rates
    const grouped = runs.reduce((acc, run) => {
      const date = new Date(run.created_at).toLocaleDateString();
      if (!acc[date]) {
        acc[date] = { date, success: 0, failed: 0, total: 0 };
      }
      acc[date].total++;
      if (run.status === 'success') {
        acc[date].success++;
      } else if (run.status === 'failed') {
        acc[date].failed++;
      }
      return acc;
    }, {} as Record<string, { date: string; success: number; failed: number; total: number }>);

    return Object.values(grouped)
      .map(item => ({
        date: item.date,
        successRate: item.total > 0 ? (item.success / item.total) * 100 : 0,
        failureRate: item.total > 0 ? (item.failed / item.total) * 100 : 0,
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime());
  }, [runs]);

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={300}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id="colorSuccess" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="colorFailed" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="date" 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
        />
        <YAxis 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          domain={[0, 100]}
          label={{ value: 'Rate (%)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#e2e8f0',
          }}
          labelStyle={{ color: '#e2e8f0' }}
          formatter={(value: number) => [`${value.toFixed(1)}%`, '']}
        />
        <Legend
          wrapperStyle={{ color: '#e2e8f0' }}
          iconType="circle"
        />
        <Area
          type="monotone"
          dataKey="successRate"
          name="Success Rate"
          stroke="#10b981"
          strokeWidth={2}
          fill="url(#colorSuccess)"
        />
        <Area
          type="monotone"
          dataKey="failureRate"
          name="Failure Rate"
          stroke="#ef4444"
          strokeWidth={2}
          fill="url(#colorFailed)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
