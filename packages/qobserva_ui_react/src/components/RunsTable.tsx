import { useNavigate } from 'react-router-dom';
import { Download } from 'lucide-react';
import { Run } from '../services/api';
import { format } from 'date-fns';
import { exportRunsToCSV } from '../utils/export';
import CopyableRunId from './CopyableRunId';

interface Props {
  runs: Run[];
  highlightShots?: boolean; // When true, highlight shots column and show run_id
  title?: string; // Optional title for export filename
  showDownloadButton?: boolean; // Show download button inline with heading
}

export default function RunsTable({ runs, highlightShots = false, title, showDownloadButton = false }: Props) {
  const navigate = useNavigate();

  const handleRowClick = (runId: string) => {
    navigate(`/runs/${runId}`);
  };

  const handleDownload = () => {
    const filename = title ? `qobserva-${title.toLowerCase().replace(/\s+/g, '-')}` : 'qobserva-runs';
    exportRunsToCSV(runs, filename);
  };

  return (
    <div>
      {showDownloadButton && (
        <div className="flex justify-end mb-4">
          <button
            onClick={handleDownload}
            className="btn-secondary flex items-center gap-2"
            title="Download as CSV"
          >
            <Download size={16} />
            Download CSV
          </button>
        </div>
      )}
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
            <th className={`text-left py-3 px-4 text-sm font-semibold ${
              highlightShots ? 'text-primary bg-primary/10' : 'text-dark-text-muted'
            }`}>
              Shots
            </th>
          </tr>
        </thead>
        <tbody>
          {runs.slice(0, 50).map((run) => (
            <tr
              key={run.run_id}
              onClick={() => handleRowClick(run.run_id)}
              className="border-b border-dark-border hover:bg-primary/10 hover:border-primary/30 cursor-pointer transition-all duration-150"
            >
              <td className="py-3 px-4 text-sm text-dark-text">
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
              <td className={`py-3 px-4 text-sm font-semibold ${
                highlightShots ? 'text-primary bg-primary/5' : 'text-dark-text'
              }`}>
                {run.shots.toLocaleString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  );
}

// Export download button component for inline use with headings
export function RunsTableDownloadButton({ runs, title }: { runs: Run[]; title?: string }) {
  const handleDownload = () => {
    const filename = title ? `qobserva-${title.toLowerCase().replace(/\s+/g, '-')}` : 'qobserva-runs';
    exportRunsToCSV(runs, filename);
  };

  return (
    <button
      onClick={handleDownload}
      className="btn-secondary flex items-center gap-2 ml-auto"
      title="Download as CSV"
    >
      <Download size={16} />
      Download CSV
    </button>
  );
}
