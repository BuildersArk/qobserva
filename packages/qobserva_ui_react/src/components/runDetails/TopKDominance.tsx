import MetricCard from '../MetricCard';

interface Props {
  top1: number;
  top5: number;
  top10: number;
}

export default function TopKDominance({ top1, top5, top10 }: Props) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Top-K Dominance</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Probability mass in top states. High values indicate algorithm convergence; low values suggest noise-dominated output.
      </p>
      <div className="grid grid-cols-3 gap-4">
        <MetricCard 
          label="Top-1 Probability" 
          value={`${(top1 * 100).toFixed(3)}%`}
        />
        <MetricCard 
          label="Top-5 Cumulative" 
          value={`${(top5 * 100).toFixed(3)}%`}
        />
        <MetricCard 
          label="Top-10 Cumulative" 
          value={`${(top10 * 100).toFixed(3)}%`}
        />
      </div>
      {top1 < 0.01 && top10 < 0.05 && (
        <p className="text-sm text-warning mt-4">
          ⚠️ Highly uniform distribution → likely noise-dominated
        </p>
      )}
    </div>
  );
}
