import { useState, useMemo, useEffect } from 'react';
import { useSearchParams, useLocation, useNavigate } from 'react-router-dom';
import { Download, Printer } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import DateRangePicker from './DateRangePicker';
import { exportRunsToCSV } from '../utils/export';

interface Props {
  onFilterChange?: (filters: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
    algorithm?: string;
  }) => void;
  disabled?: boolean; // Disable filters (e.g., for run details, compare pages)
  disabledMessage?: string; // Tooltip message when disabled
  visible?: {
    project?: boolean;
    provider?: boolean;
    status?: boolean;
    time?: boolean;
    algorithm?: boolean;
  };
  showExport?: boolean;
}

export default function FilterRibbon({
  onFilterChange,
  disabled = false,
  disabledMessage = "Filters are not available for individual run details or comparisons",
  visible = { project: true, provider: true, status: true, time: true, algorithm: false },
  showExport = true,
}: Props) {
  const [searchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const { data: runs = [] } = useQuery({
    queryKey: ['runs'],
    queryFn: () => apiService.getRuns({ limit: 1000 }),
  });
  
  // Fetch algorithms if algorithm filter is visible
  const { data: algorithms = [] } = useQuery({
    queryKey: ['algorithms'],
    queryFn: () => apiService.getAlgorithms(),
    enabled: visible.algorithm === true,
  });

  // Check if we're on FilteredRuns page
  const isFilteredRunsPage = location.pathname === '/runs-filtered';

  // Initialize filter state from URL params if present
  const urlProject = searchParams.get('project');
  const urlProvider = searchParams.get('provider');
  const urlStatus = searchParams.get('status');
  const urlStartDate = searchParams.get('startDate');
  const urlEndDate = searchParams.get('endDate');
  const urlAlgorithm = searchParams.get('algorithm');
  
  const [project, setProject] = useState(urlProject || 'All');
  const [provider, setProvider] = useState(urlProvider || 'All');
  const [status, setStatus] = useState(urlStatus || 'All');
  const [algorithm, setAlgorithm] = useState(urlAlgorithm || 'All');
  const [timeRange, setTimeRange] = useState('All Time');
  const [startDate, setStartDate] = useState<string | undefined>(urlStartDate || undefined);
  const [endDate, setEndDate] = useState<string | undefined>(urlEndDate || undefined);

  // If certain filters are hidden on this page (e.g. Analytics), ensure they don't
  // silently keep affecting the global filter state.
  useEffect(() => {
    if (visible.provider === false && provider !== 'All') setProvider('All');
    if (visible.status === false && status !== 'All') setStatus('All');
    if (visible.algorithm === false && algorithm !== 'All') setAlgorithm('All');
    // Note: we intentionally do NOT clear project/time when hidden; those are meaningful.
  }, [visible.provider, visible.status, visible.algorithm]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync filter state with URL params when they change (especially important on FilteredRuns page)
  useEffect(() => {
    // Update provider
    if (urlProvider) {
      if (urlProvider !== provider) {
        setProvider(urlProvider);
      }
    } else if (provider !== 'All') {
      setProvider('All');
    }
    
    // Update project
    if (urlProject) {
      if (urlProject !== project) {
        setProject(urlProject);
      }
    } else if (project !== 'All') {
      setProject('All');
    }
    
    // Update status
    if (urlStatus) {
      if (urlStatus !== status) {
        setStatus(urlStatus);
      }
    } else if (status !== 'All') {
      setStatus('All');
    }
    
    // Update dates
    if (urlStartDate !== startDate) {
      setStartDate(urlStartDate || undefined);
    }
    if (urlEndDate !== endDate) {
      setEndDate(urlEndDate || undefined);
    }
    
    // Update timeRange based on dates
    if (!urlStartDate && !urlEndDate && timeRange !== 'All Time') {
      setTimeRange('All Time');
    } else if ((urlStartDate || urlEndDate) && timeRange === 'All Time') {
      setTimeRange('Custom');
    }
  }, [urlProvider, urlProject, urlStatus, urlStartDate, urlEndDate, isFilteredRunsPage]); // eslint-disable-line react-hooks/exhaustive-deps

  // Extract unique values for dropdowns
  const projects = useMemo(() => {
    const unique = Array.from(new Set(runs.map(r => r.project))).sort();
    return unique;
  }, [runs]);

  const providers = useMemo(() => {
    const unique = Array.from(new Set(runs.map(r => r.provider))).sort();
    return unique;
  }, [runs]);

  const statuses = useMemo(() => {
    const unique = Array.from(new Set(runs.map(r => r.status))).sort();
    return unique;
  }, [runs]);

  const updateFilters = () => {
    const filters = {
      project: visible.project === false || project === 'All' ? undefined : project,
      provider: visible.provider === false || provider === 'All' ? undefined : provider,
      status: visible.status === false || status === 'All' ? undefined : status,
      algorithm: visible.algorithm === false || algorithm === 'All' ? undefined : algorithm,
      startDate: visible.time === false ? undefined : startDate,
      endDate: visible.time === false ? undefined : endDate,
    };
    onFilterChange?.(filters);

    // If on FilteredRuns page, also update URL params so FilteredRuns can react
    if (isFilteredRunsPage) {
      const newParams = new URLSearchParams(searchParams);
      
      // Preserve the 'type' param
      const type = searchParams.get('type');
      if (type) {
        newParams.set('type', type);
      }
      
      // Update URL params with current filters
      if (filters.project) {
        newParams.set('project', filters.project);
      } else {
        newParams.delete('project');
      }
      
      if (filters.provider) {
        newParams.set('provider', filters.provider);
      } else {
        newParams.delete('provider');
      }
      
      if (filters.status) {
        newParams.set('status', filters.status);
      } else {
        newParams.delete('status');
      }
      
      if (filters.startDate) {
        newParams.set('startDate', filters.startDate);
      } else {
        newParams.delete('startDate');
      }
      
      if (filters.endDate) {
        newParams.set('endDate', filters.endDate);
      } else {
        newParams.delete('endDate');
      }
      
      if (filters.algorithm) {
        newParams.set('algorithm', filters.algorithm);
      } else {
        newParams.delete('algorithm');
      }
      
      // Update URL without navigation (replace to avoid adding to history)
      navigate(`/runs-filtered?${newParams.toString()}`, { replace: true });
    }
  };

  const handleProjectChange = (value: string) => {
    setProject(value);
    // Update filters after state is set - use useEffect to sync
  };

  const handleProviderChange = (value: string) => {
    setProvider(value);
    // Update filters after state is set - use useEffect to sync
  };

  const handleStatusChange = (value: string) => {
    setStatus(value);
    // Update filters after state is set - use useEffect to sync
  };

  const handleAlgorithmChange = (value: string) => {
    setAlgorithm(value);
    // Update filters after state is set - use useEffect to sync
  };

  const handleTimeRangeChange = (value: string) => {
    setTimeRange(value);
    
    if (value === 'All Time') {
      // Clear date filters for "All Time"
      setStartDate(undefined);
      setEndDate(undefined);
    } else if (value === 'Custom') {
      // Don't change dates when switching to Custom - let user pick
      // The DateRangePicker will handle setting dates
    } else {
      // For preset ranges, calculate dates
      const now = new Date();
      let start: Date | null = null;
      
      switch (value) {
        case 'Last 24 Hours':
          start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
          break;
        case 'Last 7 Days':
          start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
          break;
        case 'Last 30 Days':
          start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
          break;
      }
      
      // Convert to ISO string format matching database format
      const newStartDate = start ? start.toISOString().replace(/\.\d{3}Z$/, 'Z').replace('+00:00', 'Z') : undefined;
      const newEndDate = now.toISOString().replace('+00:00', 'Z');
      setStartDate(newStartDate);
      setEndDate(newEndDate);
    }
  };

  const handleDateRangeChange = (start?: string, end?: string) => {
    // Convert date strings (YYYY-MM-DD) to ISO format matching database format
    // Database stores dates like: 2024-01-06T00:00:00Z (RFC3339 with Z, no milliseconds)
    let startISO: string | undefined;
    let endISO: string | undefined;
    
    if (start) {
      // Format: YYYY-MM-DDTHH:mm:ssZ (no milliseconds to match database format)
      const startDate = new Date(start + 'T00:00:00.000Z');
      const iso = startDate.toISOString();
      // Remove milliseconds and ensure Z format: 2024-01-06T00:00:00Z
      startISO = iso.replace(/\.\d{3}Z$/, 'Z').replace('+00:00', 'Z');
    }
    
    if (end) {
      // Set to end of day: YYYY-MM-DDTHH:mm:ssZ
      const endDate = new Date(end + 'T23:59:59.999Z');
      const iso = endDate.toISOString();
      // Keep milliseconds for end date to ensure we capture all runs on that day
      endISO = iso.replace('+00:00', 'Z');
    }
    
    setStartDate(startISO);
    setEndDate(endISO);
    setTimeRange('Custom');
    // Update filters after state is set - use useEffect to sync
  };

  // Sync filter changes to parent component whenever any filter state changes
  useEffect(() => {
    updateFilters();
  }, [project, provider, status, algorithm, startDate, endDate]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="bg-dark-surface border-b border-dark-border px-6 py-4 flex items-center gap-4">
      <div 
        className="flex items-center gap-4 flex-1"
        title={disabled ? disabledMessage : undefined}
      >
        {visible.project !== false && (
          <select
            value={project}
            onChange={(e) => handleProjectChange(e.target.value)}
            disabled={disabled}
            className={`bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <option value="All">All Projects</option>
            {projects.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        )}
        
        {visible.provider !== false && (
          <select
            value={provider}
            onChange={(e) => handleProviderChange(e.target.value)}
            disabled={disabled}
            className={`bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <option value="All">All Providers</option>
            {providers.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        )}
        
        {visible.status !== false && (
          <select
            value={status}
            onChange={(e) => handleStatusChange(e.target.value)}
            disabled={disabled}
            className={`bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <option value="All">All Statuses</option>
            {statuses.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}
        
        {visible.algorithm === true && algorithms.length > 0 && (
          <select
            value={algorithm}
            onChange={(e) => handleAlgorithmChange(e.target.value)}
            disabled={disabled}
            className={`bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <option value="All">All Algorithms</option>
            {algorithms.map((algo) => (
              <option key={algo.name} value={algo.name}>
                {algo.name} ({algo.count})
              </option>
            ))}
          </select>
        )}
        
        {visible.time !== false && (
          <select
            value={timeRange}
            onChange={(e) => handleTimeRangeChange(e.target.value)}
            disabled={disabled}
            className={`bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm ${
              disabled ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            <option value="All Time">All Time</option>
            <option value="Last 24 Hours">Last 24 Hours</option>
            <option value="Last 7 Days">Last 7 Days</option>
            <option value="Last 30 Days">Last 30 Days</option>
            <option value="Custom">Custom</option>
          </select>
        )}
        
        {visible.time !== false && timeRange === 'Custom' && !disabled && (
          <DateRangePicker 
            onDateRangeChange={handleDateRangeChange}
            initialStartDate={startDate ? new Date(startDate).toISOString().split('T')[0] : undefined}
            initialEndDate={endDate ? new Date(endDate).toISOString().split('T')[0] : undefined}
          />
        )}
      </div>
      
      <div className="flex-1" />
      
      {!disabled && showExport && (
        <ExportButton 
          filters={{
            project: visible.project === false || project === 'All' ? undefined : project,
            provider: visible.provider === false || provider === 'All' ? undefined : provider,
            status: visible.status === false || status === 'All' ? undefined : status,
            algorithm: visible.algorithm === false || algorithm === 'All' ? undefined : algorithm,
            startDate: visible.time === false ? undefined : startDate,
            endDate: visible.time === false ? undefined : endDate,
          }}
        />
      )}
    </div>
  );
}

// Export button component that fetches and exports filtered runs
function ExportButton({ filters }: { filters: {
  project?: string;
  provider?: string;
  status?: string;
  algorithm?: string;
  startDate?: string;
  endDate?: string;
} }) {
  const [isExporting, setIsExporting] = useState(false);
  const location = useLocation();

  const isHome = location.pathname === '/';

  const openPrintExport = () => {
    const params = new URLSearchParams();
    params.set('type', 'home');
    if (filters.project) params.set('project', filters.project);
    if (filters.startDate) params.set('startDate', filters.startDate);
    if (filters.endDate) params.set('endDate', filters.endDate);
    const url = `/report?${params.toString()}`;
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  // Fetch filtered runs for export
  const { refetch } = useQuery({
    queryKey: ['runs-export', filters],
    queryFn: () => apiService.getRuns({ 
      limit: 10000, // Get all filtered runs
      ...filters,
    }),
    enabled: false, // Don't fetch automatically, only on demand
  });

  const handleExport = async () => {
    setIsExporting(true);
    try {
      // Fetch the filtered runs
      const result = await refetch();
      const runsToExport = result.data || [];
      
      if (runsToExport.length === 0) {
        alert('No data to export with current filters');
        setIsExporting(false);
        return;
      }

      // Generate filename based on filters
      const filterParts: string[] = [];
      if (filters.project) filterParts.push(filters.project);
      if (filters.provider) filterParts.push(filters.provider);
      if (filters.status) filterParts.push(filters.status);
      const filename = filterParts.length > 0 
        ? `qobserva-${filterParts.join('-')}` 
        : 'qobserva-all-runs';
      
      // Export to CSV
      exportRunsToCSV(runsToExport, filename);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Failed to export data. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  if (isHome) {
    return (
      <button
        onClick={openPrintExport}
        className="btn-secondary flex items-center gap-2"
        title="Export dashboard via browser print (Save as PDF)"
      >
        <Printer size={16} />
        Export PDF
      </button>
    );
  }

  return (
    <button 
      onClick={handleExport}
      disabled={isExporting}
      className="btn-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
      title="Export filtered runs to CSV"
    >
      <Download size={16} />
      {isExporting ? 'Exporting...' : 'Export'}
    </button>
  );
}
