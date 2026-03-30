import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

interface Props {
  counts: Record<string, number>;
}

export default function CountsChart({ counts }: Props) {
  const data = Object.entries(counts)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 20)
    .map(([bitstring, count]) => ({ bitstring, count }));

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No counts available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          dataKey="bitstring" 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          angle={-45}
          textAnchor="end"
          height={80}
          label={{ 
            value: 'Bitstring (Measurement Outcome)', 
            position: 'insideBottom', 
            offset: -5, 
            fill: '#94a3b8',
            style: { textAnchor: 'middle' }
          }}
        />
        <YAxis 
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          label={{ 
            value: 'Count (Number of Observations)', 
            angle: -90, 
            position: 'insideLeft', 
            fill: '#94a3b8',
            style: { textAnchor: 'middle' }
          }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#e2e8f0', fontWeight: 'bold' }}
          formatter={(value: number) => [value.toLocaleString(), 'Count']}
        />
        <Bar dataKey="count" fill="#3b82f6" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
