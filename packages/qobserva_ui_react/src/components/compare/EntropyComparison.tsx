import { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Analysis } from '../../services/api';

interface Props {
  runA: { analysis: Analysis; runId: string; label: string };
  runB: { analysis: Analysis; runId: string; label: string };
}

export default function EntropyComparison({ runA, runB }: Props) {
  const metricsA = useMemo(() => {
    // We need event for calculateRunMetrics, but we only need entropy ratio here
    // For now, just get entropy from analysis
    return {
      entropy: runA.analysis.metrics?.['qc.quality.shannon_entropy_bits'],
      entropyRatio: undefined, // Would need event for this
    };
  }, [runA]);
  
  const metricsB = useMemo(() => {
    return {
      entropy: runB.analysis.metrics?.['qc.quality.shannon_entropy_bits'],
      entropyRatio: undefined,
    };
  }, [runB]);

  if (metricsA.entropy === undefined && metricsB.entropy === undefined) {
    return null;
  }

  const data = [
    {
      metric: 'Shannon Entropy',
      [runA.label]: metricsA.entropy || 0,
      [runB.label]: metricsB.entropy || 0,
    },
  ];

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Entropy Comparison</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Shannon entropy measures the randomness/uniformity of measurement distributions.
      </p>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={data}>
          <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
          <XAxis 
            dataKey="metric" 
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
          />
          <YAxis 
            stroke="#94a3b8"
            tick={{ fill: '#94a3b8', fontSize: 12 }}
            label={{ value: 'Entropy (bits)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
            labelStyle={{ color: '#e2e8f0' }}
            formatter={(value: number) => [`${value.toFixed(4)} bits`, 'Entropy']}
          />
          <Legend wrapperStyle={{ color: '#e2e8f0' }} />
          <Bar dataKey={runA.label} fill="#3b82f6" radius={[8, 8, 0, 0]} />
          <Bar dataKey={runB.label} fill="#10b981" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
