import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Run } from '../../services/api';

interface Props {
  runs: Run[];
}

export default function BackendPerformance({ runs }: Props) {
  const barData = useMemo(() => {
    const backendStats = runs.reduce((acc, run) => {
      if (!acc[run.backend_name]) {
        acc[run.backend_name] = { success: 0, total: 0 };
      }
      acc[run.backend_name].total++;
      if (run.status === 'success') {
        acc[run.backend_name].success++;
      }
      return acc;
    }, {} as Record<string, { success: number; total: number }>);

    return Object.entries(backendStats)
      .map(([backend, stats]) => ({
        backend,
        successRate: stats.total > 0 ? (stats.success / stats.total) * 100 : 0,
        totalRuns: stats.total,
      }))
      .sort((a, b) => b.successRate - a.successRate);
  }, [runs]);

  if (barData.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={barData}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="backend" 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          angle={-45}
          textAnchor="end"
          height={80}
        />
        <YAxis 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          domain={[0, 100]}
          label={{ value: 'Success Rate (%)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#e2e8f0' }}
        />
        <Bar dataKey="successRate" fill="#3b82f6" radius={[8, 8, 0, 0]}>
          {barData.map((_entry, index) => (
            <Bar key={`bar-${index}`} dataKey="successRate" fill="#3b82f6" />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
