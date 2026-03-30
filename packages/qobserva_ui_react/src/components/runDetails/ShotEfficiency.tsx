import MetricCard from '../MetricCard';

interface Props {
  uniqueStates: number;
  shots: number;
  uniqueStatesRatio: number;
  collisionRate: number;
}

export default function ShotEfficiency({ uniqueStates, shots, uniqueStatesRatio, collisionRate }: Props) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Shot Efficiency & Sampling Quality</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Unique states vs total shots. High unique ratio indicates undersampling; low ratio with high collisions suggests concentration.
      </p>
      <div className="grid grid-cols-2 gap-4 mb-4">
        <MetricCard 
          label="Unique States" 
          value={uniqueStates.toLocaleString()}
        />
        <MetricCard 
          label="Total Shots" 
          value={shots.toLocaleString()}
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <MetricCard 
          label="Unique/Shots Ratio" 
          value={`${(uniqueStatesRatio * 100).toFixed(2)}%`}
          change={uniqueStatesRatio > 0.9 ? 'Undersampled' : uniqueStatesRatio < 0.1 ? 'Oversampled' : 'Balanced'}
        />
        <MetricCard 
          label="Collision Rate" 
          value={`${(collisionRate * 100).toFixed(2)}%`}
          change={collisionRate > 0.5 ? 'High concentration' : 'Low concentration'}
        />
      </div>
      {uniqueStatesRatio > 0.9 && (
        <p className="text-sm text-warning mt-4">
          ⚠️ High unique ratio ({uniqueStatesRatio > 0.9 ? '>90%' : '>50%'}) - Additional shots unlikely to improve signal
        </p>
      )}
    </div>
  );
}
