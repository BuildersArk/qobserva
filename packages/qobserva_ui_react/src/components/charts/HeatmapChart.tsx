import { useMemo } from 'react';
import { Run } from '../../services/api';

// Simple heatmap using divs since Recharts doesn't have built-in heatmap
export default function HeatmapChart({ runs }: { runs: Run[] }) {
  const heatmapData = useMemo(() => {
    const backendStats = runs.reduce((acc, run) => {
      if (!acc[run.backend_name]) {
        acc[run.backend_name] = { success: 0, total: 0 };
      }
      acc[run.backend_name].total++;
      if (run.status === 'success') {
        acc[run.backend_name].success++;
      }
      return acc;
    }, {} as Record<string, { success: number; total: number }>);

    return Object.entries(backendStats).map(([backend, stats]) => ({
      backend,
      successRate: stats.total > 0 ? (stats.success / stats.total) * 100 : 0,
      totalRuns: stats.total,
    }));
  }, [runs]);

  if (heatmapData.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  const maxSuccess = Math.max(...heatmapData.map(d => d.successRate));

  return (
    <div className="space-y-4">
      {heatmapData.map((item) => (
        <div key={item.backend} className="flex items-center gap-4">
          <div className="w-32 text-sm text-dark-text">{item.backend}</div>
          <div className="flex-1 h-8 bg-dark-bg rounded-full overflow-hidden relative">
            <div
              className="h-full transition-all"
              style={{
                width: `${(item.successRate / maxSuccess) * 100}%`,
                backgroundColor: item.successRate > 70 
                  ? '#10b981' 
                  : item.successRate > 40 
                  ? '#f59e0b' 
                  : '#ef4444',
              }}
            />
            <div className="absolute inset-0 flex items-center justify-center text-xs font-semibold text-dark-text">
              {item.successRate.toFixed(1)}% ({item.totalRuns} runs)
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
