interface Props {
  options: Record<string, any>;
}

/** Readable chips for the error suppression / mitigation settings a Qiskit Runtime run used. */
export function optionChips(options: Record<string, any>): Array<{ label: string; on: boolean }> {
  const chips: Array<{ label: string; on: boolean }> = [];
  const tw = options.twirling || {};
  if (tw.enable_gates !== undefined && tw.enable_gates !== null) {
    chips.push({ label: 'Gate twirling', on: !!tw.enable_gates });
  }
  if (tw.enable_measure !== undefined && tw.enable_measure !== null) {
    chips.push({ label: 'Measurement twirling', on: !!tw.enable_measure });
  }
  const dd = options.dynamical_decoupling || {};
  if (dd.enable !== undefined && dd.enable !== null) {
    chips.push({ label: dd.enable && dd.sequence_type ? `Dynamical decoupling (${dd.sequence_type})` : 'Dynamical decoupling', on: !!dd.enable });
  }
  if (options.resilience_level !== undefined && options.resilience_level !== null) {
    chips.push({ label: `Resilience level ${options.resilience_level}`, on: Number(options.resilience_level) > 0 });
  }
  const res = options.resilience || {};
  if (res.measure_mitigation !== undefined && res.measure_mitigation !== null) {
    chips.push({ label: 'Measurement mitigation', on: !!res.measure_mitigation });
  }
  if (res.zne_mitigation !== undefined && res.zne_mitigation !== null) {
    chips.push({ label: 'ZNE', on: !!res.zne_mitigation });
  }
  if (res.pec_mitigation !== undefined && res.pec_mitigation !== null) {
    chips.push({ label: 'PEC', on: !!res.pec_mitigation });
  }
  return chips;
}

export default function ExecutionOptions({ options }: Props) {
  const chips = optionChips(options);
  const shots = options.default_shots;
  const precision = options.default_precision;
  if (chips.length === 0 && shots == null && precision == null) return null;

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Execution Options</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        Error suppression and mitigation settings the primitive ran with. Enabled settings are highlighted.
      </p>
      <div className="flex flex-wrap gap-2">
        {chips.map((c) => (
          <span
            key={c.label}
            className={`px-2 py-1 rounded text-xs font-semibold ${
              c.on ? 'bg-success/20 text-success' : 'bg-dark-bg text-dark-text-muted line-through'
            }`}
          >
            {c.label}
          </span>
        ))}
        {shots != null && (
          <span className="px-2 py-1 rounded text-xs font-semibold bg-primary/20 text-primary">
            Default shots {Number(shots).toLocaleString()}
          </span>
        )}
        {precision != null && (
          <span className="px-2 py-1 rounded text-xs font-semibold bg-primary/20 text-primary">
            Default precision {String(precision)}
          </span>
        )}
      </div>
    </div>
  );
}
