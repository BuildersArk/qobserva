import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { Search, ArrowRight } from 'lucide-react';
import { apiService } from '../services/api';
import CopyableRunId from '../components/CopyableRunId';
import { format } from 'date-fns';
import logoImage from '../assets/images/qoblogo.png';

export default function SearchRuns() {
  const [searchTerm, setSearchTerm] = useState('');
  const navigate = useNavigate();

  const { data: runs = [], isLoading } = useQuery({
    queryKey: ['runs'],
    queryFn: () => apiService.getRuns({ limit: 10000 }),
    staleTime: 5000,
  });

  const filteredRuns = runs.filter(run => {
    if (!searchTerm.trim()) return false;
    const term = searchTerm.toLowerCase();
    return (
      run.run_id.toLowerCase().includes(term) ||
      run.project.toLowerCase().includes(term) ||
      run.provider.toLowerCase().includes(term) ||
      run.backend_name.toLowerCase().includes(term) ||
      run.status.toLowerCase().includes(term)
    );
  });

  const handleRunClick = (runId: string) => {
    navigate(`/runs/${runId}`);
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && filteredRuns.length === 1) {
      // If only one result, navigate directly
      handleRunClick(filteredRuns[0].run_id);
    }
  };

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">Search Runs</h1>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
          />
        </div>
        <p className="text-dark-text-muted">Search for runs by ID, project, provider, backend, or status</p>
      </div>

      {/* Search Input */}
      <div className="card">
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-dark-text-muted" size={20} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Enter run ID, project, provider, backend, or status..."
            className="w-full bg-dark-bg border border-dark-border rounded-lg pl-12 pr-4 py-3 text-dark-text text-lg focus:outline-none focus:border-primary/50"
            autoFocus
          />
        </div>
        {searchTerm && (
          <p className="text-sm text-dark-text-muted mt-3">
            {isLoading ? 'Searching...' : `${filteredRuns.length} run${filteredRuns.length !== 1 ? 's' : ''} found`}
            {filteredRuns.length === 1 && ' (Press Enter to view)'}
          </p>
        )}
      </div>

      {/* Results */}
      {searchTerm && (
        <div className="card">
          {isLoading ? (
            <div className="text-center py-12 text-dark-text-muted">Searching...</div>
          ) : filteredRuns.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-dark-text-muted mb-2">No runs found</p>
              <p className="text-sm text-dark-text-muted">Try a different search term</p>
            </div>
          ) : (
            <div className="space-y-2">
              <h3 className="text-lg font-semibold text-white mb-4">Results</h3>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-dark-border">
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Run ID</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Time</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Project</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Provider</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Backend</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Status</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Shots</th>
                      <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredRuns.slice(0, 100).map((run) => (
                      <tr
                        key={run.run_id}
                        className="border-b border-dark-border hover:bg-primary/10 hover:border-primary/30 transition-all duration-150"
                      >
                        <td className="py-3 px-4 text-sm text-dark-text" onClick={(e) => e.stopPropagation()}>
                          <CopyableRunId runId={run.run_id} />
                        </td>
                        <td className="py-3 px-4 text-sm text-dark-text">
                          {format(new Date(run.created_at), 'MMM dd, HH:mm')}
                        </td>
                        <td className="py-3 px-4 text-sm text-dark-text">{run.project}</td>
                        <td className="py-3 px-4 text-sm text-dark-text">{run.provider}</td>
                        <td className="py-3 px-4 text-sm text-dark-text">{run.backend_name}</td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-1 rounded text-xs font-semibold ${
                              run.status === 'success'
                                ? 'bg-success/20 text-success'
                                : run.status === 'failed'
                                ? 'bg-error/20 text-error'
                                : 'bg-dark-text-muted/20 text-dark-text-muted'
                            }`}
                          >
                            {run.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-sm text-dark-text">{run.shots.toLocaleString()}</td>
                        <td className="py-3 px-4">
                          <button
                            onClick={() => handleRunClick(run.run_id)}
                            className="flex items-center gap-1 text-primary hover:text-primary/80 text-sm transition-colors"
                            title="View run details"
                          >
                            View
                            <ArrowRight size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {filteredRuns.length > 100 && (
                <p className="text-sm text-dark-text-muted mt-4 text-center">
                  Showing first 100 results. Refine your search to see more.
                </p>
              )}
            </div>
          )}
        </div>
      )}

      {/* Help Text */}
      {!searchTerm && (
        <div className="card">
          <h3 className="text-lg font-semibold text-white mb-4">How to Search</h3>
          <ul className="space-y-2 text-sm text-dark-text-muted">
            <li>• <strong className="text-dark-text">By Run ID:</strong> Enter the full or partial run ID</li>
            <li>• <strong className="text-dark-text">By Project:</strong> Search by project name</li>
            <li>• <strong className="text-dark-text">By Provider:</strong> Filter by provider (e.g., "ibm", "aws")</li>
            <li>• <strong className="text-dark-text">By Backend:</strong> Search by backend name</li>
            <li>• <strong className="text-dark-text">By Status:</strong> Filter by status (e.g., "success", "failed")</li>
          </ul>
        </div>
      )}
    </div>
  );
}
