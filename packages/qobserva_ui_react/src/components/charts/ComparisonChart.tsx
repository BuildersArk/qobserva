import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';

interface Props {
  runAId: string;
  runBId: string;
}

export default function ComparisonChart({ runAId, runBId }: Props) {
  // Get project from runs list
  const { data: runs = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: () => apiService.getRuns({ limit: 1000 }),
  });

  const runAInfo = runs.find(r => r.run_id === runAId);
  const runBInfo = runs.find(r => r.run_id === runBId);
  const projectA = runAInfo?.project || 'default';
  const projectB = runBInfo?.project || 'default';

  const { data: runA, isLoading: loadingA, error: errorA } = useQuery({
    queryKey: ['run', runAId],
    queryFn: () => apiService.getRun(projectA, runAId),
    enabled: !!runAId,
    retry: 2,
  });
  
  const { data: runB, isLoading: loadingB, error: errorB } = useQuery({
    queryKey: ['run', runBId],
    queryFn: () => apiService.getRun(projectB, runBId),
    enabled: !!runBId,
    retry: 2,
  });

  if (loadingA || loadingB) {
    return <div className="text-center py-12 text-dark-text-muted">Loading run data...</div>;
  }

  if (errorA || errorB || !runA || !runB) {
    return (
      <div className="text-center py-12 text-dark-text-muted">
        {errorA || errorB ? 'Error loading run data' : 'Run data not found'}
      </div>
    );
  }

  const data = [
    {
      metric: 'Runtime (ms)',
      'Run A': runA.event.execution.runtime_ms || 0,
      'Run B': runB.event.execution.runtime_ms || 0,
    },
    {
      metric: 'Queue (ms)',
      'Run A': runA.event.execution.queue_ms || 0,
      'Run B': runB.event.execution.queue_ms || 0,
    },
    {
      metric: 'Shots',
      'Run A': runA.event.execution.shots,
      'Run B': runB.event.execution.shots,
    },
  ];

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Metric Comparison</h3>
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
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#1e293b',
              border: '1px solid #334155',
              borderRadius: '8px',
            }}
          />
          <Legend wrapperStyle={{ color: '#e2e8f0' }} />
          <Bar dataKey="Run A" fill="#3b82f6" radius={[8, 8, 0, 0]} />
          <Bar dataKey="Run B" fill="#8b5cf6" radius={[8, 8, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
