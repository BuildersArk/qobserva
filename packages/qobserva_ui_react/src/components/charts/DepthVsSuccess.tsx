import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { Run } from '../../services/api';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import { useNavigate } from 'react-router-dom';

interface Props {
  runs: Run[];
}

export default function DepthVsSuccess({ runs }: Props) {
  const navigate = useNavigate();
  // Fetch analysis data for each run to get depth metrics
  const runAnalyses = useQuery({
    queryKey: ['runs-analyses', runs.map(r => r.run_id)],
    queryFn: async () => {
      const pairs = await Promise.all(
        runs.slice(0, 50).map(async (run) => {
          const res = await apiService.getRun(run.project, run.run_id).catch(() => null);
          if (!res) return null;
          return { run, res };
        })
      );
      return pairs.filter(Boolean) as Array<{ run: Run; res: any }>;
    },
  });

  const data = runAnalyses.data
    ?.map(({ run, res }) => {
      const depth = res?.analysis?.metrics?.['qc.circuit.depth.post'];
      const success = res?.analysis?.metrics?.['qc.quality.success_probability'];
      if (depth && success !== undefined) {
        return {
          depth,
          success: success * 100,
          backend: run.backend_name,
          runId: run.run_id,
          project: run.project,
        };
      }
      return null;
    })
    .filter(Boolean) || [];

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          type="number"
          dataKey="depth" 
          name="Circuit Depth"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          label={{ value: 'Circuit Depth', position: 'insideBottom', offset: -5, fill: '#94a3b8' }}
        />
        <YAxis 
          type="number"
          dataKey="success" 
          name="Success Rate"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          label={{ value: 'Success Rate (%)', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
        />
        <Tooltip
          cursor={{ strokeDasharray: '3 3' }}
          contentStyle={{
            backgroundColor: '#1e293b',
            border: '1px solid #334155',
            borderRadius: '8px',
            color: '#e2e8f0',
          }}
          itemStyle={{ color: '#e2e8f0' }}
          labelStyle={{ color: '#e2e8f0' }}
        />
        <Scatter
          dataKey="success"
          fill="#3b82f6"
          onClick={(state: any) => {
            const p = state?.payload;
            if (p?.runId) navigate(`/runs/${p.runId}`);
          }}
          style={{ cursor: 'pointer' }}
        >
          {data.map((_entry, index) => (
            <Cell key={`cell-${index}`} fill="#3b82f6" />
          ))}
        </Scatter>
      </ScatterChart>
    </ResponsiveContainer>
  );
}
