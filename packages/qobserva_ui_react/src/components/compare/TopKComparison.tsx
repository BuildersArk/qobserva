import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Event, Analysis } from '../../services/api';
import { calculateRunMetrics } from '../../utils/runMetrics';

interface Props {
  runA: { event: Event; analysis: Analysis; runId: string; label: string };
  runB: { event: Event; analysis: Analysis; runId: string; label: string };
}

export default function TopKComparison({ runA, runB }: Props) {
  const metricsA = useMemo(() => calculateRunMetrics(runA.event, runA.analysis), [runA]);
  const metricsB = useMemo(() => calculateRunMetrics(runB.event, runB.analysis), [runB]);

  const data = [
    {
      category: 'Top-1',
      [runA.label]: metricsA.top1Probability ? metricsA.top1Probability * 100 : 0,
      [runB.label]: metricsB.top1Probability ? metricsB.top1Probability * 100 : 0,
    },
    {
      category: 'Top-5',
      [runA.label]: metricsA.top5Probability ? metricsA.top5Probability * 100 : 0,
      [runB.label]: metricsB.top5Probability ? metricsB.top5Probability * 100 : 0,
    },
    {
      category: 'Top-10',
      [runA.label]: metricsA.top10Probability ? metricsA.top10Probability * 100 : 0,
      [runB.label]: metricsB.top10Probability ? metricsB.top10Probability * 100 : 0,
    },
  ];

  if (!metricsA.top1Probability && !metricsB.top1Probability) {
    return null;
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Top-K Dominance Comparison</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Probability mass in top states. Higher values indicate better algorithm convergence.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="category" 
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
          />
          <YAxis 
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            label={{ value: 'Probability (%)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(value: number) => [`${value.toFixed(3)}%`, 'Probability']}
          />
          <Legend wrapperStyle={{ color: '#e2e8f0' }} />
          <Bar dataKey={runA.label} fill="#3b82f6" radius={[8, 8, 0, 0]} />
          <Bar dataKey={runB.label} fill="#10b981" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
