import type { Run } from '../services/api';

// Display names for the SDK names the agent records (D-Wave is recorded as "dwave_ocean").
const SDK_LABELS: Record<string, string> = {
  qiskit: 'Qiskit',
  braket: 'Braket',
  cirq: 'Cirq',
  pennylane: 'PennyLane',
  pyquil: 'pyQuil',
  dwave: 'D-Wave',
  dwave_ocean: 'D-Wave',
};

/** The run's SDK for display; "—" for runs from collectors older than 0.1.6 that did not send it. */
export function sdkLabel(run: Pick<Run, 'sdk' | 'summary'>): string {
  const name = run.sdk || run.summary?.sdk;
  if (!name) return '—';
  return SDK_LABELS[name.toLowerCase()] || name;
}
