/**
 * Shots and queue time as recorded, without inventing values.
 * - Runs computed exactly (execution.exact: statevector Estimator, PennyLane analytic, Braket shots=0)
 *   sampled no shots; their event carries shots=1 only for schema compatibility, and the runs list has 0.
 * - Queue time is known when the provider reported it (queue_ms) or the run was on a local simulator
 *   (no queue); otherwise it was not reported.
 */
export const EXACT_TOOLTIP = 'Computed exactly by the simulator; no shots were sampled';

export function sampledShots(execution: { shots?: number; exact?: boolean } | undefined): number {
  if (!execution) return 0;
  return execution.exact ? 0 : execution.shots || 0;
}

export function shotsLabel(shots: number | undefined, exact?: boolean): string {
  return exact ? 'Exact' : (shots || 0).toLocaleString();
}

export function knownQueueMs(event: any): number | undefined {
  const queueMs = event?.execution?.queue_ms;
  if (typeof queueMs === 'number') return queueMs;
  return event?.backend?.provider === 'local_sim' ? 0 : undefined;
}
