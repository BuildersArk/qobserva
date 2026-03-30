import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Run } from '../../services/api';

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

export default function BackendRadar({ runs, baseFilters }: Props) {
  const navigate = useNavigate();
  const { chartData, backends } = useMemo(() => {
    // Group by backend and calculate metrics
    const backendStats = new Map<string, {
      total: number;
      success: number;
      totalShots: number;
    }>();
    
    runs.forEach(run => {
      const backend = run.backend_name;
      if (!backendStats.has(backend)) {
        backendStats.set(backend, { total: 0, success: 0, totalShots: 0 });
      }
      
      const stats = backendStats.get(backend)!;
      stats.total += 1;
      if (run.status === 'success') stats.success += 1;
      stats.totalShots += run.shots || 0;
    });
    
    // Get top 5 backends by total runs
    const topBackends = Array.from(backendStats.entries())
      .sort((a, b) => b[1].total - a[1].total)
      .slice(0, 5);
    
    // Get max values for normalization
    const maxRuns = Math.max(...topBackends.map(([_, stats]) => stats.total), 1);
    const maxShots = Math.max(...topBackends.map(([_, stats]) => stats.totalShots / stats.total), 1);
    
    // Prepare backend data
    const backendData = topBackends.map(([backend, stats]) => ({
      backend: backend.length > 15 ? backend.substring(0, 15) + '...' : backend,
      'Success Rate': stats.total > 0 ? (stats.success / stats.total) * 100 : 0,
      'Total Runs': (stats.total / maxRuns) * 100,
      'Avg Shots': stats.total > 0 ? Math.min((stats.totalShots / stats.total / maxShots) * 100, 100) : 0,
    }));
    
    // Convert to radar chart format - each row is a metric dimension
    const metrics = ['Success Rate', 'Total Runs', 'Avg Shots'];
    const chartData = metrics.map(metric => {
      const entry: any = { metric };
      backendData.forEach(backend => {
        entry[backend.backend] = backend[metric as keyof typeof backend];
      });
      return entry;
    });
    
    return { chartData, backends: backendData.map(b => b.backend) };
  }, [runs]);

  if (chartData.length === 0 || backends.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

  return (
    <ResponsiveContainer width="100%" height={400}>
      <RadarChart data={chartData}>
        <PolarGrid stroke="#334155" />
        <PolarAngleAxis 
          dataKey="metric" 
          tick={{ fill: '#94a3b8', fontSize: 12 }}
        />
        <PolarRadiusAxis 
          angle={90} 
          domain={[0, 100]}
          tick={{ fill: '#94a3b8', fontSize: 10 }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
          }}
          labelStyle={{ color: '#e2e8f0' }}
        />
        <Legend
          wrapperStyle={{ color: '#e2e8f0', cursor: 'pointer' }}
          onClick={() => navigate(`/runs-filtered${toQuery(baseFilters, { type: 'backends' })}`)}
        />
        {backends.map((backend, idx) => (
          <Radar
            key={backend}
            name={backend}
            dataKey={backend}
            stroke={colors[idx % colors.length]}
            fill={colors[idx % colors.length]}
            fillOpacity={0.3}
            style={{ cursor: 'pointer' }}
            onClick={() => navigate(`/runs-filtered${toQuery(baseFilters, { type: 'backends' })}`)}
          />
        ))}
      </RadarChart>
    </ResponsiveContainer>
  );
}
