import { useMemo } from 'react';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { Run } from '../../services/api';

interface Props {
  runs: Run[];
}

export default function ShotsDistribution({ runs }: Props) {
  const data = useMemo(() => {
    // Categorize runs by shots range
    const categories = {
      '0-100': 0,
      '101-1K': 0,
      '1K-10K': 0,
      '10K-100K': 0,
      '100K+': 0,
    };
    
    runs.forEach(run => {
      const shots = run.shots || 0;
      if (shots <= 100) {
        categories['0-100']++;
      } else if (shots <= 1000) {
        categories['101-1K']++;
      } else if (shots <= 10000) {
        categories['1K-10K']++;
      } else if (shots <= 100000) {
        categories['10K-100K']++;
      } else {
        categories['100K+']++;
      }
    });
    
    return Object.entries(categories)
      .filter(([_, count]) => count > 0)
      .map(([name, value]) => ({ name, value }));
  }, [runs]);

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={120}
          fill="#8884d8"
          dataKey="value"
        >
          {data.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#e2e8f0',
          }}
          labelStyle={{ color: '#e2e8f0' }}
          itemStyle={{ color: '#e2e8f0' }}
          formatter={(value: number) => [value, 'Runs']}
        />
        <Legend wrapperStyle={{ color: '#e2e8f0' }} />
      </PieChart>
    </ResponsiveContainer>
  );
}
