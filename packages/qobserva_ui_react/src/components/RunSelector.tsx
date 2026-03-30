import { useState, useMemo } from 'react';
import { Run } from '../services/api';
import { format } from 'date-fns';
import { Search, X } from 'lucide-react';

interface Props {
  runs: Run[];
  value: string;
  onChange: (runId: string) => void;
  label: string;
  placeholder?: string;
}

export default function RunSelector({ runs, value, onChange, label, placeholder = "Search by run ID, project, backend..." }: Props) {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const selectedRun = runs.find(r => r.run_id === value);

  const filteredRuns = useMemo(() => {
    if (!searchTerm.trim()) {
      return runs.slice(0, 50); // Show first 50 when no search
    }
    
    const term = searchTerm.toLowerCase();
    return runs.filter(run => 
      run.run_id.toLowerCase().includes(term) ||
      run.project.toLowerCase().includes(term) ||
      run.provider.toLowerCase().includes(term) ||
      run.backend_name.toLowerCase().includes(term) ||
      run.status.toLowerCase().includes(term)
    ).slice(0, 50);
  }, [runs, searchTerm]);

  const handleSelect = (runId: string) => {
    onChange(runId);
    setIsOpen(false);
    setSearchTerm('');
  };

  const handleClear = () => {
    onChange('');
    setSearchTerm('');
  };

  return (
    <div className="relative">
      <label className="block text-sm font-medium text-dark-text-muted mb-2">
        {label}
      </label>
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm flex items-center justify-between hover:border-primary/50 transition-colors"
        >
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <Search size={16} className="text-dark-text-muted flex-shrink-0" />
            {selectedRun ? (
              <span className="truncate">
                <span className="font-mono text-xs text-primary">{selectedRun.run_id.substring(0, 12)}...</span>
                {' '}
                <span className="text-dark-text-muted">•</span>
                {' '}
                <span>{selectedRun.project}</span>
                {' '}
                <span className="text-dark-text-muted">•</span>
                {' '}
                <span>{selectedRun.backend_name}</span>
                {' '}
                <span className="text-dark-text-muted">•</span>
                {' '}
                <span className="text-xs">{format(new Date(selectedRun.created_at), 'MMM dd, HH:mm')}</span>
              </span>
            ) : (
              <span className="text-dark-text-muted">{placeholder}</span>
            )}
          </div>
          {selectedRun && (
            <div
              onClick={(e) => {
                e.stopPropagation();
                handleClear();
              }}
              className="ml-2 text-dark-text-muted hover:text-dark-text transition-colors cursor-pointer flex items-center"
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.stopPropagation();
                  handleClear();
                }
              }}
            >
              <X size={16} />
            </div>
          )}
        </button>

        {isOpen && (
          <>
            <div 
              className="fixed inset-0 z-10" 
              onClick={() => setIsOpen(false)}
            />
            <div className="absolute z-20 w-full mt-1 bg-dark-surface border border-dark-border rounded-lg shadow-xl max-h-96 overflow-hidden">
              <div className="p-2 border-b border-dark-border">
                <div className="relative">
                  <Search size={16} className="absolute left-3 top-1/2 transform -translate-y-1/2 text-dark-text-muted" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Type to search..."
                    className="w-full bg-dark-bg border border-dark-border rounded-lg pl-10 pr-3 py-2 text-dark-text text-sm focus:outline-none focus:border-primary/50"
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                  />
                </div>
              </div>
              <div className="overflow-y-auto max-h-80">
                {filteredRuns.length === 0 ? (
                  <div className="p-4 text-center text-dark-text-muted text-sm">
                    No runs found
                  </div>
                ) : (
                  <div className="p-1">
                    {filteredRuns.map((run) => (
                      <button
                        key={run.run_id}
                        onClick={() => handleSelect(run.run_id)}
                        className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors ${
                          run.run_id === value
                            ? 'bg-primary/20 text-primary border border-primary/30'
                            : 'text-dark-text hover:bg-dark-bg'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-2">
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="font-mono text-xs text-primary font-semibold">
                                {run.run_id.substring(0, 12)}...
                              </span>
                              <span className={`px-2 py-0.5 rounded text-xs font-semibold ${
                                run.status === 'success'
                                  ? 'bg-success/20 text-success'
                                  : run.status === 'failed'
                                  ? 'bg-error/20 text-error'
                                  : 'bg-dark-text-muted/20 text-dark-text-muted'
                              }`}>
                                {run.status}
                              </span>
                            </div>
                            <div className="text-xs text-dark-text-muted space-x-2">
                              <span>{run.project}</span>
                              <span>•</span>
                              <span>{run.provider}</span>
                              <span>•</span>
                              <span>{run.backend_name}</span>
                              <span>•</span>
                              <span>{format(new Date(run.created_at), 'MMM dd, HH:mm')}</span>
                            </div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
