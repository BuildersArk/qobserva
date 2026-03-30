import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/api';
import CountsChart from './CountsChart';

interface Props {
  runAId: string;
  runBId: string;
}

export default function SideBySideCounts({ runAId, runBId }: Props) {
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

  return (
    <div className="grid grid-cols-2 gap-6">
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Run A: Counts</h3>
        <CountsChart counts={runA.event.artifacts?.counts?.histogram || {}} />
      </div>
      
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Run B: Counts</h3>
        <CountsChart counts={runB.event.artifacts?.counts?.histogram || {}} />
      </div>
    </div>
  );
}
