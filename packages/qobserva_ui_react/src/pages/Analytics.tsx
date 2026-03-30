import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import DepthVsSuccess from '../components/charts/DepthVsSuccess';
import CostQualityScatter from '../components/charts/CostQualityScatter';
import HeatmapChart from '../components/charts/HeatmapChart';
import GaugeChart from '../components/charts/GaugeChart';
// BackendPerformance chart available for future use
// import BackendPerformance from '../components/charts/BackendPerformance';
import ProviderPerformanceLine from '../components/charts/ProviderPerformanceLine';
import RuntimeTrend from '../components/charts/RuntimeTrend';
import BackendRadar from '../components/charts/BackendRadar';
import ShotsDistribution from '../components/charts/ShotsDistribution';
import logoImage from '../assets/images/qoblogo.png';

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

function toQuery(filters?: Props['filters'], extra?: Record<string, string | undefined>) {
  const params = new URLSearchParams();
  const merged = { ...(filters || {}), ...(extra || {}) };
  Object.entries(merged).forEach(([k, v]) => {
    if (v) params.set(k, v);
  });
  const qs = params.toString();
  return qs ? `?${qs}` : '';
}

export default function Analytics({ filters }: Props) {
  const navigate = useNavigate();
  
  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs', filters],
    queryFn: () => apiService.getRuns({ limit: 1000, ...(filters || {}) }),
    staleTime: 5000,
  });

  if (isLoading) {
    return <div className="text-center py-12 text-dark-text-muted">Loading...</div>;
  }

  const handleGaugeClick = (type: string) => {
    if (type === 'success') {
      navigate(`/runs-filtered${toQuery(filters, { type: 'success' })}`);
    } else if (type === 'backends') {
      navigate(`/runs-filtered${toQuery(filters, { type: 'backends' })}`);
    } else if (type === 'runs') {
      navigate(`/runs-filtered${toQuery(filters)}`);
    }
  };

  const successRate = runs.length > 0 ? (runs.filter(r => r.status === 'success').length / runs.length * 100) : 0;
  const uniqueBackends = new Set(runs.map(r => r.backend_name)).size;

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">Run Analytics</h1>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
          />
        </div>
        <p className="text-dark-text-muted">Comprehensive analysis and trends of quantum run performance</p>
      </div>
      
      {/* KPI Gauge Charts */}
      <div className="grid grid-cols-3 gap-6">
        <div 
          className="card cursor-pointer hover:border-primary/50 transition-colors"
          onClick={() => handleGaugeClick('success')}
        >
          <h3 className="text-lg font-semibold mb-4 text-white">Overall Success Rate</h3>
          <GaugeChart 
            value={successRate}
            label="Success Rate"
          />
          <p className="text-xs text-dark-text-muted mt-2 text-center">Click to view successful runs</p>
        </div>
        <div 
          className="card cursor-pointer hover:border-primary/50 transition-colors"
          onClick={() => handleGaugeClick('backends')}
        >
          <h3 className="text-lg font-semibold mb-4 text-white">Active Backends</h3>
          <GaugeChart 
            value={uniqueBackends}
            label="Backends"
            max={Math.max(uniqueBackends, 10)}
          />
          <p className="text-xs text-dark-text-muted mt-2 text-center">Click to view backend statistics</p>
        </div>
        <div 
          className="card cursor-pointer hover:border-primary/50 transition-colors"
          onClick={() => handleGaugeClick('runs')}
        >
          <h3 className="text-lg font-semibold mb-4 text-white">Total Runs</h3>
          <GaugeChart 
            value={runs.length}
            label="Runs"
            max={Math.max(runs.length, 1000)}
          />
          <p className="text-xs text-dark-text-muted mt-2 text-center">Click to view all runs</p>
        </div>
      </div>

      {/* Line Charts - Performance Trends */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Provider Performance Over Time</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Track run volume across different providers over time
          </p>
          <ProviderPerformanceLine runs={runs} baseFilters={filters} />
        </div>
        
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Average Runtime Trend</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Monitor average execution time trends over time
          </p>
          <RuntimeTrend runs={runs} baseFilters={filters} />
        </div>
      </div>

      {/* Radar Chart - Multi-dimensional Backend Comparison */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">Backend Multi-Dimensional Analysis</h3>
        <p className="text-sm text-dark-text-muted mb-4">
          Compare backends across multiple performance dimensions
        </p>
        <BackendRadar runs={runs} baseFilters={filters} />
      </div>

      {/* Scatter Plots */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Circuit Depth vs Success</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Relationship between circuit complexity and success rate
          </p>
          <DepthVsSuccess runs={runs} />
        </div>
        
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Cost vs Quality Trade-off</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Analyze the balance between execution cost and result quality
          </p>
          <CostQualityScatter runs={runs} />
        </div>
      </div>

      {/* Distribution Charts */}
      <div className="grid grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Shots Distribution</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Distribution of runs by shots range
          </p>
          <ShotsDistribution runs={runs} />
        </div>
        
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 text-white">Backend Performance Heatmap</h3>
          <p className="text-sm text-dark-text-muted mb-4">
            Heatmap showing backend performance patterns
          </p>
          <HeatmapChart runs={runs} />
        </div>
      </div>
    </div>
  );
}
