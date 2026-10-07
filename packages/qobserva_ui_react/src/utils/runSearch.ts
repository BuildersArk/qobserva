import { Run } from '../services/api';
import { sdkLabel } from './sdk';

/** True when the run's ID, job ID, project, SDK, provider, backend or status contains the search term. */
export function matchesRunSearch(run: Run, searchTerm: string): boolean {
  const term = searchTerm.trim().toLowerCase();
  if (!term) return true;
  return (
    run.run_id.toLowerCase().includes(term) ||
    run.project.toLowerCase().includes(term) ||
    run.provider.toLowerCase().includes(term) ||
    run.backend_name.toLowerCase().includes(term) ||
    run.status.toLowerCase().includes(term) ||
    sdkLabel(run).toLowerCase().includes(term) ||
    (run.job_id || '').toLowerCase().includes(term)
  );
}
