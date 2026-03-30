/**
 * Calculate metrics from run event data
 */

export interface RunMetrics {
  // Top-K dominance
  top1Probability: number;
  top5Probability: number;
  top10Probability: number;
  
  // Effective support size
  effectiveSupportSize: number; // States covering 95% probability
  
  // Entropy metrics
  entropy: number;
  idealEntropy: number; // Max entropy for qubit count
  entropyRatio: number; // entropy / idealEntropy
  
  // Shot efficiency
  uniqueStates: number;
  uniqueStatesRatio: number; // uniqueStates / shots
  collisionRate: number; // % of shots landing in already-seen states
  
  // Runtime metrics
  runtimePerShot: number; // runtime_ms / shots
  runtimeClassification: 'cpu-bound' | 'queue-dominated' | 'execution-dominated' | 'unknown';
}

/**
 * Calculate all run metrics from event data
 */
export function calculateRunMetrics(event: any, analysis: any): Partial<RunMetrics> {
  const metrics: Partial<RunMetrics> = {};
  
  const counts = event.artifacts?.counts?.histogram || {};
  const shots = event.execution?.shots || 0;
  const runtimeMs = event.execution?.runtime_ms || 0;
  const queueMs = event.execution?.queue_ms || 0;
  const numQubits = event.program?.circuit_metrics?.num_qubits;
  
  if (!counts || shots === 0) {
    return metrics;
  }
  
  // Convert counts to probabilities and sort
  const probabilities = Object.entries(counts)
    .map(([state, count]: [string, any]) => ({
      state,
      count: parseInt(count, 10),
      probability: parseInt(count, 10) / shots,
    }))
    .sort((a, b) => b.probability - a.probability);
  
  // 1. Top-K dominance
  if (probabilities.length > 0) {
    metrics.top1Probability = probabilities[0].probability;
    
    const top5 = probabilities.slice(0, 5).reduce((sum, p) => sum + p.probability, 0);
    metrics.top5Probability = top5;
    
    const top10 = probabilities.slice(0, 10).reduce((sum, p) => sum + p.probability, 0);
    metrics.top10Probability = top10;
  }
  
  // 2. Effective support size (95% probability mass)
  let cumulativeProb = 0;
  let effectiveSupportSize = 0;
  for (const p of probabilities) {
    cumulativeProb += p.probability;
    effectiveSupportSize++;
    if (cumulativeProb >= 0.95) {
      break;
    }
  }
  metrics.effectiveSupportSize = effectiveSupportSize;
  
  // 3. Entropy vs ideal entropy
  const entropy = analysis.metrics?.['qc.quality.shannon_entropy_bits'];
  if (entropy !== undefined && entropy !== null) {
    metrics.entropy = entropy;
    
    if (numQubits && numQubits > 0) {
      const idealEntropy = numQubits; // Max entropy for n qubits is n bits
      metrics.idealEntropy = idealEntropy;
      metrics.entropyRatio = entropy / idealEntropy;
    }
  }
  
  // 4. Unique states vs shots
  const uniqueStates = Object.keys(counts).length;
  metrics.uniqueStates = uniqueStates;
  metrics.uniqueStatesRatio = shots > 0 ? uniqueStates / shots : 0;
  
  // 5. Collision rate
  // Collision = shots that landed in states that were already seen
  // We can approximate this as: (shots - uniqueStates) / shots
  // But more accurately: sum of (count - 1) for all states with count > 1
  let collisions = 0;
  for (const count of Object.values(counts)) {
    const c = parseInt(String(count), 10);
    if (c > 1) {
      collisions += c - 1;
    }
  }
  metrics.collisionRate = shots > 0 ? collisions / shots : 0;
  
  // 6. Runtime per shot
  if (runtimeMs > 0 && shots > 0) {
    metrics.runtimePerShot = runtimeMs / shots;
  }
  
  // 7. Runtime classification (heuristic)
  if (runtimeMs > 0) {
    const totalTime = runtimeMs + queueMs;
    if (totalTime > 0) {
      const queueRatio = queueMs / totalTime;
      const runtimeRatio = runtimeMs / totalTime;
      
      if (queueRatio > 0.5) {
        metrics.runtimeClassification = 'queue-dominated';
      } else if (runtimeRatio > 0.7) {
        metrics.runtimeClassification = 'execution-dominated';
      } else if (runtimeMs < 100 && queueMs < 100) {
        // Very fast execution, likely CPU-bound
        metrics.runtimeClassification = 'cpu-bound';
      } else {
        metrics.runtimeClassification = 'unknown';
      }
    } else {
      metrics.runtimeClassification = 'unknown';
    }
  } else {
    metrics.runtimeClassification = 'unknown';
  }
  
  return metrics;
}
