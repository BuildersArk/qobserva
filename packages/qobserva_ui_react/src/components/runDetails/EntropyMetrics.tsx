import MetricCard from '../MetricCard';

interface Props {
  entropy: number;
  idealEntropy?: number;
  entropyRatio?: number;
}

export default function EntropyMetrics({ entropy, idealEntropy, entropyRatio }: Props) {
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4 text-white">Entropy Analysis</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Measured entropy vs ideal (max) entropy. Ratio shows "how random" relative to expectation.
      </p>
      <div className="grid grid-cols-3 gap-4">
        <MetricCard 
          label="Shannon Entropy" 
          value={`${entropy.toFixed(4)} bits`}
        />
        {idealEntropy !== undefined && (
          <MetricCard 
            label="Ideal Entropy (Max)" 
            value={`${idealEntropy.toFixed(4)} bits`}
          />
        )}
        {entropyRatio !== undefined && (
          <MetricCard 
            label="Entropy Ratio" 
            value={`${(entropyRatio * 100).toFixed(1)}%`}
            change={entropyRatio > 0.9 ? 'Highly random' : entropyRatio > 0.5 ? 'Moderately random' : 'Concentrated'}
          />
        )}
      </div>
      {entropyRatio !== undefined && (
        <div className="mt-4">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-dark-text-muted">Randomness:</span>
            <span className={`font-semibold ${
              entropyRatio > 0.9 ? 'text-warning' : entropyRatio > 0.5 ? 'text-primary' : 'text-success'
            }`}>
              {entropyRatio > 0.9 ? 'Highly Random' : entropyRatio > 0.5 ? 'Moderately Random' : 'Concentrated'}
            </span>
          </div>
          <div className="w-full bg-dark-bg rounded-full h-2">
            <div 
              className={`h-2 rounded-full transition-all ${
                entropyRatio > 0.9 ? 'bg-warning' : entropyRatio > 0.5 ? 'bg-primary' : 'bg-success'
              }`}
              style={{ width: `${entropyRatio * 100}%` }}
            />
          </div>
        </div>
      )}
    </div>
  );
}
