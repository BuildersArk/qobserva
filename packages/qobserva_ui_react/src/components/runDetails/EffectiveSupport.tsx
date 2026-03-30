import MetricCard from '../MetricCard';

interface Props {
  effectiveSupportSize: number;
  totalStates: number;
}

export default function EffectiveSupport({ effectiveSupportSize, totalStates }: Props) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Effective Support Size</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Number of states covering 95% of probability mass. More intuitive than entropy for understanding algorithm sharpness vs noise.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <MetricCard 
          label="Effective Support (95%)" 
          value={effectiveSupportSize.toLocaleString()}
        />
        <MetricCard 
          label="Total Unique States" 
          value={totalStates.toLocaleString()}
        />
      </div>
      <div className="mt-4">
        <div className="flex items-center justify-between text-sm mb-2">
          <span className="text-dark-text-muted">Coverage:</span>
          <span className="text-dark-text">
            {totalStates > 0 ? ((effectiveSupportSize / totalStates) * 100).toFixed(1) : 0}% of states
          </span>
        </div>
        <div className="w-full bg-dark-bg rounded-full h-2">
          <div 
            className="bg-primary h-2 rounded-full transition-all"
            style={{ width: `${totalStates > 0 ? (effectiveSupportSize / totalStates) * 100 : 0}%` }}
          />
        </div>
      </div>
    </div>
  );
}
