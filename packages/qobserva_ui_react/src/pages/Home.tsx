import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import MetricCard from '../components/MetricCard';
import StatusDistribution from '../components/charts/StatusDistribution';
import RunsTable, { RunsTableDownloadButton } from '../components/RunsTable';
import SuccessTrend from '../components/charts/SuccessTrend';

interface Props {
  filters?: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
    algorithm?: string;
  };
}

export default function Home({ filters = {} }: Props) {
  const navigate = useNavigate();
  
  // All hooks must be called before any early returns
  const [filteredStatus, setFilteredStatus] = useState<string | null>(null);
  
  // Create a stable query key from filters
  const queryKey = useMemo(() => {
    return ['runs', JSON.stringify(filters)];
  }, [filters]);

  const { data: runs = [], isLoading } = useQuery({
    queryKey,
    queryFn: () => {
      return apiService.getRuns({ 
        limit: 1000, // Increased to get all filtered runs
        ...filters,
      });
    },
    staleTime: 0, // Always refetch when filters change
    refetchOnWindowFocus: false,
  });

  if (isLoading) {
    return <div className="text-center py-12 text-dark-text-muted">Loading...</div>;
  }

  // Calculate KPIs
  const totalRuns = runs.length;
  const successRuns = runs.filter(r => r.status === 'success').length;
  const avgSuccess = totalRuns > 0 ? (successRuns / totalRuns) * 100 : 0;
  const totalShots = runs.reduce((sum, r) => sum + r.shots, 0);
  const avgShots = totalRuns > 0 ? Math.round(totalShots / totalRuns) : 0;
  const uniqueBackends = new Set(runs.map(r => r.backend_name)).size;

  // Filter runs by status for pie chart click
  const displayedRuns = filteredStatus 
    ? runs.filter(r => r.status === filteredStatus)
    : runs;

  // Helper to build filter query string
  const buildFilterQuery = (type: string) => {
    const params = new URLSearchParams({ type });
    if (filters.project) params.set('project', filters.project);
    if (filters.provider) params.set('provider', filters.provider);
    if (filters.status) params.set('status', filters.status);
    if (filters.startDate) params.set('startDate', filters.startDate);
    if (filters.endDate) params.set('endDate', filters.endDate);
    return `/runs-filtered?${params.toString()}`;
  };

  return (
    <div className="space-y-8">
      {/* KPI Cards */}
      <div className="grid grid-cols-5 gap-6">
        <MetricCard 
          label="Total Runs" 
          value={totalRuns.toLocaleString()} 
          clickable
          onClick={() => navigate(buildFilterQuery('all'))}
        />
        <MetricCard 
          label="Success Rate" 
          value={`${avgSuccess.toFixed(1)}%`} 
          clickable
          onClick={() => navigate(buildFilterQuery('success'))}
        />
        <MetricCard 
          label="Avg Shots" 
          value={avgShots.toLocaleString()} 
          clickable
          onClick={() => navigate(buildFilterQuery('shots'))}
        />
        <MetricCard 
          label="Backends" 
          value={uniqueBackends.toString()} 
          clickable
          onClick={() => navigate(buildFilterQuery('backends'))}
        />
        <MetricCard 
          label="Total Shots" 
          value={totalShots.toLocaleString()} 
          clickable
          onClick={() => navigate(buildFilterQuery('shots'))}
        />
      </div>

      {/* Charts Row 1 */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Success Rate Trend</h3>
          <SuccessTrend runs={runs} />
        </div>
        
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Runs by Status</h3>
          <StatusDistribution 
            runs={runs} 
            onSliceClick={(status) => {
              setFilteredStatus(status);
            }}
          />
        </div>
      </div>

      {/* Recent Runs Table */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white">
            {filteredStatus ? `${filteredStatus.charAt(0).toUpperCase() + filteredStatus.slice(1)} Runs` : 'Recent Runs'}
            {filteredStatus && (
              <button
                onClick={() => setFilteredStatus(null)}
                className="ml-4 text-sm text-primary hover:underline"
              >
                Clear filter
              </button>
            )}
          </h3>
          <RunsTableDownloadButton runs={displayedRuns} />
        </div>
        <RunsTable runs={displayedRuns} />
      </div>
    </div>
  );
}
