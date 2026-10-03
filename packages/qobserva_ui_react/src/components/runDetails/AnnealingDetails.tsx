import MetricCard from '../MetricCard';
import type { AnnealingArtifact } from '../../services/api';

interface Props {
  annealing: AnnealingArtifact;
}

export default function AnnealingDetails({ annealing }: Props) {
  const cbf = annealing.chain_break_fraction;
  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Embedding &amp; Chain Breaks</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        How the problem was mapped onto physical qubits. Each logical variable becomes a chain of qubits;
        a broken chain means its qubits disagreed and the value had to be repaired.
      </p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {cbf != null && (
          <MetricCard label="Chain Break Fraction" value={`${(cbf * 100).toFixed(2)}%`} />
        )}
        {annealing.max_chain_length != null && (
          <MetricCard label="Max Chain Length" value={String(annealing.max_chain_length)} />
        )}
        {annealing.num_logical_variables != null && (
          <MetricCard label="Logical Variables" value={String(annealing.num_logical_variables)} />
        )}
        {annealing.num_physical_qubits != null && (
          <MetricCard label="Physical Qubits" value={String(annealing.num_physical_qubits)} />
        )}
        {annealing.mean_chain_length != null && (
          <MetricCard label="Mean Chain Length" value={annealing.mean_chain_length.toFixed(2)} />
        )}
        {annealing.chain_strength != null && (
          <MetricCard label="Chain Strength" value={annealing.chain_strength.toFixed(3)} />
        )}
        {annealing.max_chain_break_fraction != null && (
          <MetricCard label="Worst Sample Breaks" value={`${(annealing.max_chain_break_fraction * 100).toFixed(2)}%`} />
        )}
      </div>
      {cbf != null && cbf > 0.1 && (
        <p className="text-sm text-warning mt-4">
          ⚠️ More than 10% of chains broke. Consider raising chain_strength or finding a shorter embedding.
        </p>
      )}
    </div>
  );
}
