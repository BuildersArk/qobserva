import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';
import { apiService } from '../services/api';
import RunSelector from '../components/RunSelector';
import RunInfoHeader from '../components/compare/RunInfoHeader';
import MetricComparison from '../components/compare/MetricComparison';
import CountsComparison from '../components/compare/CountsComparison';
import TopKComparison from '../components/compare/TopKComparison';
import EntropyComparison from '../components/compare/EntropyComparison';
import logoImage from '../assets/images/qoblogo.png';

export default function Compare() {
  const [searchParams, setSearchParams] = useSearchParams();
  
  const { data: runs = [], isLoading: runsLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: () => apiService.getRuns({ limit: 1000 }),
    staleTime: 5000,
  });

  // Initialize from URL params or defaults
  const [runAId, setRunAId] = useState(() => searchParams.get('runA') || '');
  const [runBId, setRunBId] = useState(() => searchParams.get('runB') || '');

  // Set defaults when runs load (only once, if no URL params)
  useEffect(() => {
    if (runs.length > 0 && !runAId && !runBId && !searchParams.get('runA') && !searchParams.get('runB')) {
      const defaultA = runs[0]?.run_id || '';
      const defaultB = runs.length > 1 ? (runs[1]?.run_id || '') : defaultA;
      setRunAId(defaultA);
      setRunBId(defaultB);
      setSearchParams({ runA: defaultA, runB: defaultB }, { replace: true });
    }
  }, [runs, runAId, runBId, searchParams, setSearchParams]);

  // Update URL params when selections change
  useEffect(() => {
    const params = new URLSearchParams();
    if (runAId) params.set('runA', runAId);
    if (runBId) params.set('runB', runBId);
    setSearchParams(params, { replace: true });
  }, [runAId, runBId, setSearchParams]);

  // Get run info for project lookup
  const runAInfo = runs.find(r => r.run_id === runAId);
  const runBInfo = runs.find(r => r.run_id === runBId);
  const projectA = runAInfo?.project || 'default';
  const projectB = runBInfo?.project || 'default';

  // Fetch full run data
  const { data: runAData, isLoading: loadingA } = useQuery({
    queryKey: ['run', runAId],
    queryFn: () => apiService.getRun(projectA, runAId),
    enabled: !!runAId,
    retry: 2,
  });

  const { data: runBData, isLoading: loadingB } = useQuery({
    queryKey: ['run', runBId],
    queryFn: () => apiService.getRun(projectB, runBId),
    enabled: !!runBId,
    retry: 2,
  });

  if (runsLoading) {
    return <div className="text-center py-12 text-dark-text-muted">Loading runs...</div>;
  }

  const isLoading = loadingA || loadingB;
  const hasData = runAData && runBData;

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">Compare Runs</h1>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
          />
        </div>
        <p className="text-dark-text-muted">Select two runs to compare metrics, quality, and performance</p>
      </div>
      
      {/* Run Selectors */}
      <div className="grid grid-cols-2 gap-6">
        <RunSelector
          runs={runs}
          value={runAId}
          onChange={setRunAId}
          label="Run A"
          placeholder="Search for first run..."
        />
        <RunSelector
          runs={runs}
          value={runBId}
          onChange={setRunBId}
          label="Run B"
          placeholder="Search for second run..."
        />
      </div>

      {/* Comparison Content */}
      {isLoading && (
        <div className="text-center py-12 text-dark-text-muted">Loading run data...</div>
      )}

      {!isLoading && hasData && runAId && runBId && (
        <>
          {/* Run Info Headers */}
          <div className="grid grid-cols-2 gap-6">
            <RunInfoHeader 
              event={runAData.event} 
              runId={runAId}
              label="Run A"
            />
            <RunInfoHeader 
              event={runBData.event} 
              runId={runBId}
              label="Run B"
            />
          </div>

          {/* Metric Comparisons */}
          <MetricComparison 
            runA={runAData}
            runB={runBData}
          />

          {/* Top-K Dominance Comparison */}
          <TopKComparison
            runA={{ event: runAData.event, analysis: runAData.analysis, runId: runAId, label: 'Run A' }}
            runB={{ event: runBData.event, analysis: runBData.analysis, runId: runBId, label: 'Run B' }}
          />

          {/* Entropy Comparison */}
          <EntropyComparison
            runA={{ analysis: runAData.analysis, runId: runAId, label: 'Run A' }}
            runB={{ analysis: runBData.analysis, runId: runBId, label: 'Run B' }}
          />

          {/* Measurement Results Comparison */}
          <CountsComparison
            runA={{ event: runAData.event, runId: runAId, label: 'Run A' }}
            runB={{ event: runBData.event, runId: runBId, label: 'Run B' }}
          />
        </>
      )}

      {!isLoading && !hasData && (runAId || runBId) && (
        <div className="text-center py-12 text-dark-text-muted">
          Please select both runs to compare
        </div>
      )}
    </div>
  );
}
