import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Download } from 'lucide-react';
import { Run } from '../services/api';
import { exportBackendsToCSV } from '../utils/export';

interface Props {
  runs: Run[];
}

interface BackendStats {
  backend_name: string;
  provider: string;
  total: number;
  success: number;
  failed: number;
  cancelled: number;
}

export default function BackendsTable({ runs }: Props) {
  const navigate = useNavigate();

  const backendStats = useMemo(() => {
    const statsMap = new Map<string, BackendStats>();
    
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
      if (run.status === 'success') {
        stats.success++;
      } else if (run.status === 'failed') {
        stats.failed++;
      } else if (run.status === 'cancelled') {
        stats.cancelled++;
      }
    });
    
    return Array.from(statsMap.values()).sort((a, b) => b.total - a.total);
  }, [runs]);

  const handleBackendClick = (provider: string) => {
    // Navigate back to home with provider filter applied
    navigate(`/?provider=${encodeURIComponent(provider)}`);
  };

  if (backendStats.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No backend data available</div>;
  }

  return (
    <div>
      <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-dark-border">
            <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Backend Name</th>
            <th className="text-left py-3 px-4 text-sm font-semibold text-dark-text-muted">Provider</th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Total Runs</th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Success</th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Failed</th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Cancelled</th>
            <th className="text-right py-3 px-4 text-sm font-semibold text-dark-text-muted">Success Rate</th>
          </tr>
        </thead>
        <tbody>
          {backendStats.map((backend) => {
            const successRate = backend.total > 0 ? (backend.success / backend.total) * 100 : 0;
            return (
              <tr
                key={backend.backend_name}
                onClick={() => handleBackendClick(backend.provider)}
                className="border-b border-dark-border hover:bg-primary/10 hover:border-primary/30 cursor-pointer transition-all duration-150"
              >
                <td className="py-3 px-4 text-sm text-dark-text font-medium">
                  {backend.backend_name}
                </td>
                <td className="py-3 px-4 text-sm text-dark-text">
                  {backend.provider}
                </td>
                <td className="py-3 px-4 text-sm text-dark-text text-right">
                  {backend.total.toLocaleString()}
                </td>
                <td className="py-3 px-4 text-right">
                  <span className="text-sm text-success font-medium">
                    {backend.success.toLocaleString()}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <span className="text-sm text-error font-medium">
                    {backend.failed.toLocaleString()}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <span className="text-sm text-dark-text-muted font-medium">
                    {backend.cancelled.toLocaleString()}
                  </span>
                </td>
                <td className="py-3 px-4 text-right">
                  <span className={`text-sm font-semibold ${
                    successRate >= 80 ? 'text-success' : successRate >= 50 ? 'text-warning' : 'text-error'
                  }`}>
                    {successRate.toFixed(1)}%
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
      </div>
    </div>
  );
}

// Export download button component for inline use with headings
export function BackendsTableDownloadButton({ backendStats }: { backendStats: BackendStats[] }) {
  const handleDownload = () => {
    exportBackendsToCSV(backendStats, 'qobserva-backends');
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
