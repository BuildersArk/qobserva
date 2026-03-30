import { useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import RunsTable, { RunsTableDownloadButton } from '../components/RunsTable';
import BackendsTable, { BackendsTableDownloadButton } from '../components/BackendsTable';
import ShotsScatter from '../components/charts/ShotsScatter';
import { ArrowLeft } from 'lucide-react';
import logoImage from '../assets/images/qoblogo.png';

export default function FilteredRuns() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  
  const filterType = searchParams.get('type') || 'all';
  
  // Read all filters from URL params - use useMemo to create stable filter object
  const apiFilters = useMemo(() => {
    const filters: any = { limit: 10000 };
    
    const project = searchParams.get('project');
    const provider = searchParams.get('provider');
    const status = searchParams.get('status');
    const startDate = searchParams.get('startDate');
    const endDate = searchParams.get('endDate');
    
    if (project) filters.project = project;
    if (provider) filters.provider = provider;
    if (startDate) filters.startDate = startDate;
    if (endDate) filters.endDate = endDate;
    
    // Apply status filter based on type or explicit status param
    if (status) {
      filters.status = status;
    } else if (filterType === 'success') {
      filters.status = 'success';
    } else if (filterType === 'failed') {
      filters.status = 'failed';
    }
    
    return filters;
  }, [searchParams, filterType]); // Re-compute when URL params change
  
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs', apiFilters],
    queryFn: () => apiService.getRuns(apiFilters),
    staleTime: 0, // Always refetch when filters change
  });

  // Compute backend stats once (used when filterType === 'backends'); must run unconditionally for Rules of Hooks
  const backendStats = useMemo(() => {
    const statsMap = new Map<string, { backend_name: string; provider: string; total: number; success: number; failed: number; cancelled: number }>();
    runs.forEach((run) => {
      const key = run.backend_name;
      if (!statsMap.has(key)) {
        statsMap.set(key, {
          backend_name: run.backend_name,
          provider: run.provider,
          total: 0,
          success: 0,
          failed: 0,
          cancelled: 0,
        });
      }
      const stats = statsMap.get(key)!;
      stats.total++;
      if (run.status === 'success') stats.success++;
      else if (run.status === 'failed') stats.failed++;
      else if (run.status === 'cancelled') stats.cancelled++;
    });
    return Array.from(statsMap.values()).sort((a, b) => b.total - a.total);
  }, [runs]);

  let title = 'All Runs';
  if (filterType === 'success') {
    title = 'Successful Runs';
  } else if (filterType === 'failed') {
    title = 'Failed Runs';
  } else if (filterType === 'shots') {
    title = 'Runs by Shots';
  } else if (filterType === 'backends') {
    title = 'Runs by Backend';
  } else if (status) {
    title = `${status.charAt(0).toUpperCase() + status.slice(1)} Runs`;
  }

  if (isLoading) {
    return <div className="text-center py-12 text-dark-text-muted">Loading...</div>;
  }

  // For shots type, show scatter plot instead of table
  if (filterType === 'shots') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-dark-surface rounded-lg transition-colors"
            >
              <ArrowLeft size={20} className="text-dark-text-muted" />
            </button>
            <h1 className="text-3xl font-bold text-white">{title}</h1>
            <span className="text-dark-text-muted">({runs.length} runs)</span>
          </div>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
          />
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Shots Distribution</h3>
          <ShotsScatter runs={runs} />
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Runs List</h3>
            <RunsTableDownloadButton runs={runs} title="shots-runs" />
          </div>
          <RunsTable runs={runs} highlightShots={true} title="shots-runs" />
        </div>
      </div>
    );
  }

  // For backends type, show backends table
  if (filterType === 'backends') {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button
              onClick={() => navigate(-1)}
              className="p-2 hover:bg-dark-surface rounded-lg transition-colors"
            >
              <ArrowLeft size={20} className="text-dark-text-muted" />
            </button>
            <h1 className="text-3xl font-bold text-white">{title}</h1>
            <span className="text-dark-text-muted">({runs.length} runs across {new Set(runs.map(r => r.backend_name)).size} backends)</span>
          </div>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
          />
        </div>

        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-white">Backend Statistics</h3>
            <BackendsTableDownloadButton backendStats={backendStats} />
          </div>
          <p className="text-sm text-dark-text-muted mb-4">Click on a backend row to filter by provider on the Home dashboard</p>
          <BackendsTable runs={runs} />
        </div>
      </div>
    );
  }

  // For other types, show regular runs table
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <button
          onClick={() => navigate(-1)}
          className="p-2 hover:bg-dark-surface rounded-lg transition-colors"
        >
          <ArrowLeft size={20} className="text-dark-text-muted" />
        </button>
        <h1 className="text-3xl font-bold text-white">{title}</h1>
        <span className="text-dark-text-muted">({runs.length} runs)</span>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">{title}</h3>
          <RunsTableDownloadButton runs={runs} title={title.toLowerCase().replace(/\s+/g, '-')} />
        </div>
        <RunsTable runs={runs} title={title.toLowerCase().replace(/\s+/g, '-')} />
      </div>
    </div>
  );
}
