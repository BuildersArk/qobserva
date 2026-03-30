import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, Cell } from 'recharts';
import RunsTable from '../components/RunsTable';
import logoImage from '../assets/images/qoblogo.png';

interface Props {
  filters?: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
  };
}

export default function Algorithms({ filters }: Props) {
  const navigate = useNavigate();
  const [selectedAlgorithm, setSelectedAlgorithm] = useState<string>('');

  // Fetch algorithms list
  const { data: algorithms = [], isLoading: algorithmsLoading } = useQuery({
    queryKey: ['algorithms'],
    queryFn: () => apiService.getAlgorithms(),
  });

  // Auto-select first algorithm if available
  useEffect(() => {
    if (algorithms.length > 0 && !selectedAlgorithm) {
      setSelectedAlgorithm(algorithms[0].name);
    }
  }, [algorithms, selectedAlgorithm]);

  // Fetch runs for selected algorithm
  const { data: allRuns = [], isLoading: runsLoading } = useQuery({
    queryKey: ['runs', filters, selectedAlgorithm],
    queryFn: () => apiService.getRuns({ 
      limit: 1000, 
      ...(filters || {}),
      algorithm: selectedAlgorithm || undefined,
    }),
    enabled: !!selectedAlgorithm,
  });

  // Fetch all runs to calculate overall metrics for comparison
  const { data: overallRuns = [] } = useQuery({
    queryKey: ['runs', filters],
    queryFn: () => apiService.getRuns({ limit: 1000, ...(filters || {}) }),
  });

  // Calculate derived values BEFORE conditional returns
  const algorithmRuns = allRuns;
  const runIds = useMemo(() => algorithmRuns.map(r => r.run_id), [algorithmRuns]);
  
  // Fetch event data for SDK extraction (ALWAYS call hook, conditionally enable)
  const { data: runEvents } = useQuery({
    queryKey: ['run-events', runIds],
    queryFn: async () => {
      const events = new Map<string, any>();
      // Load event data for a sample of runs (limit to avoid performance issues)
      const sampleRuns = algorithmRuns.slice(0, 100);
      await Promise.all(
        sampleRuns.map(async (run) => {
          try {
            const eventData = await apiService.getRun(run.project, run.run_id);
            events.set(run.run_id, eventData.event);
          } catch (error) {
            console.error(`Error loading event for ${run.run_id}:`, error);
          }
        })
      );
      return events;
    },
    enabled: algorithmRuns.length > 0 && algorithmRuns.length <= 100, // Only fetch if reasonable number
  });

  // --- All useMemo hooks MUST run before any conditional return ---
  const sdkComparison = useMemo(() => {
    const sdkMap = new Map<string, { success: number; total: number; totalRuntime: number; totalShots: number }>();
    algorithmRuns.forEach(run => {
      let sdk = run.provider;
      if (runEvents) {
        const event = runEvents.get(run.run_id);
        if (event?.software?.sdk?.name) sdk = event.software.sdk.name;
        else if (event?.tags?.sdk) sdk = event.tags.sdk;
      }
      if (!sdkMap.has(sdk)) sdkMap.set(sdk, { success: 0, total: 0, totalRuntime: 0, totalShots: 0 });
      const stats = sdkMap.get(sdk)!;
      stats.total++;
      if (run.status === 'success') stats.success++;
      stats.totalShots += run.shots;
      if (runEvents) {
        const event = runEvents.get(run.run_id);
        if (event?.execution?.runtime_ms) stats.totalRuntime += event.execution.runtime_ms;
      }
    });
    return Array.from(sdkMap.entries()).map(([sdk, stats]) => ({
      sdk,
      successRate: stats.total > 0 ? (stats.success / stats.total * 100) : 0,
      avgShots: stats.total > 0 ? (stats.totalShots / stats.total) : 0,
      avgRuntime: stats.total > 0 && stats.totalRuntime > 0 ? (stats.totalRuntime / stats.total) : 0,
      totalRuns: stats.total,
    })).sort((a, b) => b.totalRuns - a.totalRuns);
  }, [algorithmRuns, runEvents]);

  const performanceOverTime = useMemo(() => {
    const timeMap = new Map<string, { success: number; total: number }>();
    algorithmRuns.forEach(run => {
      const date = new Date(run.created_at).toISOString().split('T')[0];
      if (!timeMap.has(date)) timeMap.set(date, { success: 0, total: 0 });
      const stats = timeMap.get(date)!;
      stats.total++;
      if (run.status === 'success') stats.success++;
    });
    return Array.from(timeMap.entries())
      .map(([date, stats]) => ({ date, successRate: stats.total > 0 ? (stats.success / stats.total * 100) : 0, totalRuns: stats.total }))
      .sort((a, b) => a.date.localeCompare(b.date))
      .slice(-30);
  }, [algorithmRuns]);

  const backendComparison = useMemo(() => {
    const backendMap = new Map<string, { success: number; total: number }>();
    algorithmRuns.forEach(run => {
      const key = `${run.provider}/${run.backend_name}`;
      if (!backendMap.has(key)) backendMap.set(key, { success: 0, total: 0 });
      const stats = backendMap.get(key)!;
      stats.total++;
      if (run.status === 'success') stats.success++;
    });
    return Array.from(backendMap.entries())
      .map(([backend, stats]) => ({ backend, successRate: stats.total > 0 ? (stats.success / stats.total * 100) : 0, totalRuns: stats.total }))
      .sort((a, b) => b.totalRuns - a.totalRuns)
      .slice(0, 10);
  }, [algorithmRuns]);

  // avgRuntime available for future use
  // const avgRuntime = useMemo(() => 0, [algorithmRuns]);

  const algorithmMetrics = useMemo(() => {
    if (!runEvents || algorithmRuns.length === 0) return null;
    const metrics: any = { vqe: { energies: [] as number[] }, grover: { targetSuccessRates: [] as number[] }, optimization: { approximationRatios: [] as number[] } };
    algorithmRuns.slice(0, 50).forEach(run => {
      const event = runEvents.get(run.run_id);
      if (!event?.program?.benchmark_params) return;
      const params = event.program.benchmark_params;
      const algo = selectedAlgorithm.toLowerCase();
      if (algo.includes('vqe') && params.energy !== undefined) metrics.vqe.energies.push(params.energy);
      if (algo.includes('grover') && params.expected_success_rate !== undefined) metrics.grover.targetSuccessRates.push(params.expected_success_rate);
      if (algo.includes('optimization') || algo.includes('qubo') || algo.includes('ising')) {
        if (params.approximation_ratio !== undefined) metrics.optimization.approximationRatios.push(params.approximation_ratio);
      }
    });
    const hasMetrics = metrics.vqe.energies.length > 0 || metrics.grover.targetSuccessRates.length > 0 || metrics.optimization.approximationRatios.length > 0;
    return hasMetrics ? metrics : null;
  }, [algorithmRuns, runEvents, selectedAlgorithm]);

  const overallSuccessRate = overallRuns.length > 0
    ? (overallRuns.filter(r => r.status === 'success').length / overallRuns.length * 100)
    : 0;
  const algorithmSuccessRate = algorithmRuns.length > 0
    ? (algorithmRuns.filter(r => r.status === 'success').length / algorithmRuns.length * 100)
    : 0;

  const COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4'];

  // Early returns ONLY after all hooks
  if (algorithmsLoading) {
    return <div className="text-center py-12 text-dark-text-muted">Loading algorithms...</div>;
  }

  if (algorithms.length === 0) {
    return (
      <div className="space-y-8">
        <div>
          <div className="flex items-center justify-between mb-2">
            <h1 className="text-3xl font-bold text-white">Algorithm Analytics</h1>
            <img 
              src={logoImage} 
              alt="QObserva Logo" 
              className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:h-36 object-contain flex-shrink-0"
            />
          </div>
          <p className="text-dark-text-muted">Algorithm-specific performance analysis and benchmarking</p>
        </div>
        
        <div className="card text-center py-12">
          <h2 className="text-xl font-semibold text-white mb-4">No Algorithm-Tagged Runs Found</h2>
          <p className="text-dark-text-muted mb-4">
            Tag your runs with an <code className="bg-dark-bg px-2 py-1 rounded text-primary">algorithm</code> tag to see algorithm-specific metrics.
          </p>
          <p className="text-sm text-dark-text-muted">
            Example:
          </p>
          <pre className="bg-dark-bg p-4 rounded-lg text-left text-sm text-dark-text overflow-x-auto mt-4">
{`@observe_run(
    project="my_project",
    tags={
        "sdk": "qiskit",
        "algorithm": "vqe"  # Add this tag
    }
)`}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">Algorithm Analytics</h1>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:h-36 object-contain flex-shrink-0"
          />
        </div>
        <p className="text-dark-text-muted">Algorithm-specific performance analysis and cross-SDK comparison</p>
      </div>

      {/* Algorithm Selector */}
      <div className="card">
        <label className="block text-sm font-medium text-white mb-2">
          Select Algorithm
        </label>
        <select
          value={selectedAlgorithm}
          onChange={(e) => setSelectedAlgorithm(e.target.value)}
          className="bg-dark-bg border border-dark-border rounded-lg px-4 py-2 text-dark-text w-full max-w-md"
        >
          {algorithms.map((algo) => (
            <option key={algo.name} value={algo.name}>
              {algo.name} ({algo.count} runs)
            </option>
          ))}
        </select>
      </div>

      {!selectedAlgorithm ? (
        <div className="card text-center py-12">
          <p className="text-dark-text-muted">Select an algorithm to view metrics.</p>
        </div>
      ) : runsLoading ? (
        <div className="text-center py-12 text-dark-text-muted">Loading algorithm data...</div>
      ) : algorithmRuns.length === 0 ? (
        <div className="card text-center py-12">
          <p className="text-dark-text-muted">No runs found for selected algorithm with current filters.</p>
        </div>
      ) : (
        <>
          {/* Algorithm Overview Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            <div className="card">
              <h3 className="text-sm font-medium text-dark-text-muted mb-2">Total Runs</h3>
              <p className="text-3xl font-bold text-white">{algorithmRuns.length}</p>
            </div>
            <div className="card">
              <h3 className="text-sm font-medium text-dark-text-muted mb-2">Success Rate</h3>
              <p className="text-3xl font-bold text-white">{algorithmSuccessRate.toFixed(1)}%</p>
              <p className="text-xs text-dark-text-muted mt-1">
                Overall: {overallSuccessRate.toFixed(1)}%
              </p>
            </div>
            <div className="card">
              <h3 className="text-sm font-medium text-dark-text-muted mb-2">Avg Shots</h3>
              <p className="text-3xl font-bold text-white">
                {algorithmRuns.length > 0
                  ? Math.round(algorithmRuns.reduce((sum, r) => sum + r.shots, 0) / algorithmRuns.length)
                  : 0}
              </p>
            </div>
            <div className="card">
              <h3 className="text-sm font-medium text-dark-text-muted mb-2">SDKs Used</h3>
              <p className="text-3xl font-bold text-white">{sdkComparison.length}</p>
            </div>
          </div>

          {/* SDK Comparison Charts */}
          {sdkComparison.length > 0 && (
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="card">
                <h3 className="text-lg font-semibold mb-4 text-white">
                  Success Rate by SDK/Provider
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={sdkComparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="sdk" 
                      stroke="#9ca3af"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1f2937', 
                        border: '1px solid #374151',
                        color: '#f3f4f6'
                      }}
                    />
                    <Bar dataKey="successRate" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                      {sdkComparison.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <h3 className="text-lg font-semibold mb-4 text-white">
                  Average Shots by SDK/Provider
                </h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={sdkComparison}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="sdk" 
                      stroke="#9ca3af"
                      angle={-45}
                      textAnchor="end"
                      height={80}
                    />
                    <YAxis stroke="#9ca3af" />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1f2937', 
                        border: '1px solid #374151',
                        color: '#f3f4f6'
                      }}
                    />
                    <Bar dataKey="avgShots" fill="#8b5cf6" radius={[4, 4, 0, 0]}>
                      {sdkComparison.map((_entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {/* Best SDK for Algorithm */}
          {sdkComparison.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4 text-white">
                Best Performing SDK for {selectedAlgorithm}
              </h3>
              <div className="flex items-center gap-6">
                {sdkComparison
                  .sort((a, b) => b.successRate - a.successRate)
                  .slice(0, 3)
                  .map((sdk, index) => (
                    <div key={sdk.sdk} className="flex-1">
                      <div className={`p-4 rounded-lg border-2 ${
                        index === 0 
                          ? 'border-primary bg-primary/10' 
                          : 'border-dark-border bg-dark-bg'
                      }`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium text-dark-text-muted">
                            {index === 0 ? '🥇 Best' : index === 1 ? '🥈 2nd' : '🥉 3rd'}
                          </span>
                          <span className="text-xs text-dark-text-muted">{sdk.totalRuns} runs</span>
                        </div>
                        <div className="text-2xl font-bold text-white mb-1">{sdk.sdk}</div>
                        <div className="text-sm text-dark-text-muted">
                          {sdk.successRate.toFixed(1)}% success rate
                        </div>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}

          {/* Performance Over Time */}
          {performanceOverTime.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4 text-white">
                {selectedAlgorithm} Performance Over Time
              </h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={performanceOverTime}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="date" 
                    stroke="#9ca3af"
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis stroke="#9ca3af" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1f2937', 
                      border: '1px solid #374151',
                      color: '#f3f4f6'
                    }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="successRate" 
                    stroke="#3b82f6" 
                    strokeWidth={2}
                    dot={{ fill: '#3b82f6', r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Backend Analysis */}
          {backendComparison.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4 text-white">
                Backend Performance for {selectedAlgorithm}
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-dark-border">
                      <th className="text-left py-3 px-4 text-sm font-medium text-dark-text-muted">Backend</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-dark-text-muted">Runs</th>
                      <th className="text-right py-3 px-4 text-sm font-medium text-dark-text-muted">Success Rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {backendComparison.map((backend) => (
                      <tr 
                        key={backend.backend}
                        className="border-b border-dark-border hover:bg-dark-bg/50 cursor-pointer"
                        onClick={() => navigate(`/runs-filtered?algorithm=${selectedAlgorithm}&provider=${backend.backend.split('/')[0]}`)}
                      >
                        <td className="py-3 px-4 text-dark-text">{backend.backend}</td>
                        <td className="py-3 px-4 text-right text-dark-text">{backend.totalRuns}</td>
                        <td className="py-3 px-4 text-right text-dark-text">
                          {backend.successRate.toFixed(1)}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Algorithm-Specific Metrics Section */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 text-white">
              Algorithm-Specific Metrics
            </h3>
            {algorithmMetrics ? (
              <div className="space-y-4">
                {selectedAlgorithm.toLowerCase().includes('vqe') && algorithmMetrics.vqe.energies.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-dark-text-muted mb-2">VQE Energy Values</h4>
                    <div className="flex items-center gap-4">
                      <div>
                        <span className="text-xs text-dark-text-muted">Min:</span>
                        <span className="ml-2 text-white font-semibold">
                          {Math.min(...algorithmMetrics.vqe.energies).toFixed(4)}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-dark-text-muted">Max:</span>
                        <span className="ml-2 text-white font-semibold">
                          {Math.max(...algorithmMetrics.vqe.energies).toFixed(4)}
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-dark-text-muted">Avg:</span>
                        <span className="ml-2 text-white font-semibold">
                          {(algorithmMetrics.vqe.energies.reduce((a: number, b: number) => a + b, 0) / algorithmMetrics.vqe.energies.length).toFixed(4)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                {selectedAlgorithm.toLowerCase().includes('grover') && algorithmMetrics.grover.targetSuccessRates.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-dark-text-muted mb-2">Grover's Target Success Rates</h4>
                    <div className="flex items-center gap-4">
                      <div>
                        <span className="text-xs text-dark-text-muted">Avg Expected:</span>
                        <span className="ml-2 text-white font-semibold">
                          {(algorithmMetrics.grover.targetSuccessRates.reduce((a: number, b: number) => a + b, 0) / algorithmMetrics.grover.targetSuccessRates.length * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div>
                        <span className="text-xs text-dark-text-muted">Actual:</span>
                        <span className="ml-2 text-white font-semibold">
                          {algorithmSuccessRate.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                {(selectedAlgorithm.toLowerCase().includes('optimization') || 
                  selectedAlgorithm.toLowerCase().includes('qubo') || 
                  selectedAlgorithm.toLowerCase().includes('ising')) && 
                  algorithmMetrics.optimization.approximationRatios.length > 0 && (
                  <div>
                    <h4 className="text-sm font-medium text-dark-text-muted mb-2">Approximation Ratios</h4>
                    <div className="flex items-center gap-4">
                      <div>
                        <span className="text-xs text-dark-text-muted">Avg:</span>
                        <span className="ml-2 text-white font-semibold">
                          {(algorithmMetrics.optimization.approximationRatios.reduce((a: number, b: number) => a + b, 0) / algorithmMetrics.optimization.approximationRatios.length).toFixed(3)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-dark-text-muted">
                <p className="mb-2">
                  Add <code className="bg-dark-bg px-2 py-1 rounded text-primary">benchmark_params</code> to your runs to see algorithm-specific metrics.
                </p>
                <p className="text-sm">
                  Example: For VQE, include energy values; for Grover's, include target bitstrings.
                </p>
              </div>
            )}
          </div>

          {/* Algorithm Runs Table */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 text-white">
              {selectedAlgorithm} Runs
            </h3>
            <RunsTable 
              runs={algorithmRuns}
            />
          </div>
        </>
      )}
    </div>
  );
}
