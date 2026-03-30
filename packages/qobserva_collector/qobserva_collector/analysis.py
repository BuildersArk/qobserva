from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

def compute_metrics_and_insights(event: Dict[str, Any], baseline: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    metrics: Dict[str, Any] = {}
    insights: List[Dict[str, Any]] = []

    exec_ = event.get("execution", {}) or {}
    shots = int(exec_.get("shots") or 0)
    metrics["qc.shots"] = shots

    if exec_.get("runtime_ms") is not None:
        metrics["qc.time.runtime_ms"] = exec_["runtime_ms"]
    if exec_.get("queue_ms") is not None:
        metrics["qc.time.queue_ms"] = exec_["queue_ms"]

    # Execution time breakdown (e.g. IBM resource_usage: CPU, QPU, queue, post-processing)
    resource_usage = exec_.get("resource_usage")
    if isinstance(resource_usage, dict):
        for key, metric_key in [
            ("cpu_time_s", "qc.time.cpu_s"),
            ("qpu_time_s", "qc.time.qpu_s"),
            ("queue_time_s", "qc.time.queue_s"),
            ("post_processing_time_s", "qc.time.post_processing_s"),
        ]:
            val = resource_usage.get(key)
            if val is not None and isinstance(val, (int, float)):
                metrics[metric_key] = round(float(val), 3)

    cost = event.get("cost", {}) or {}
    metrics["qc.cost.estimated_usd"] = cost.get("estimated_cost")

    program = event.get("program", {}) or {}
    cm = program.get("circuit_metrics", {}) or {}
    for key in ["num_qubits", "depth_pre", "depth_post", "two_qubit_gate_count_pre", "two_qubit_gate_count_post"]:
        if key in cm and cm[key] is not None:
            metrics[f"qc.circuit.{key}"] = cm[key]
    if cm.get("depth_pre") and cm.get("depth_post"):
        metrics["qc.transpile.depth_inflation_ratio"] = cm["depth_post"] / max(1, cm["depth_pre"])

    artifacts = event.get("artifacts", {}) or {}
    counts = None
    if isinstance(artifacts.get("counts"), dict):
        counts = artifacts["counts"].get("histogram")

    targets = (program.get("benchmark_params") or {}).get("target_bitstrings")

    if isinstance(counts, dict) and shots > 0 and isinstance(targets, list) and targets:
        success = sum(int(counts.get(t, 0)) for t in targets) / shots
        metrics["qc.quality.success_probability"] = success

    if isinstance(counts, dict) and shots > 0:
        ent = 0.0
        for c in counts.values():
            p = c / shots
            if p > 0:
                ent -= p * math.log2(p)
        metrics["qc.quality.shannon_entropy_bits"] = ent

    # Energy metrics (for D-Wave/optimization problems)
    energies = artifacts.get("energies", {})
    if isinstance(energies, dict) and energies.get("value") is not None:
        energy_value = energies.get("value")
        if isinstance(energy_value, (int, float)):
            metrics["qc.optimization.energy"] = float(energy_value)
            if energies.get("stderr") is not None:
                metrics["qc.optimization.energy_stderr"] = float(energies["stderr"])
            
            # Check if we have a target/ground state energy for comparison
            benchmark_params = program.get("benchmark_params", {}) or {}
            ground_state_energy = benchmark_params.get("ground_state_energy")
            if ground_state_energy is not None:
                try:
                    ground_state = float(ground_state_energy)
                    if ground_state != 0:
                        # Approximation ratio: achieved_energy / ground_state_energy
                        # For minimization: lower is better, ratio should be >= 1.0
                        approximation_ratio = energy_value / ground_state
                        metrics["qc.optimization.approximation_ratio"] = approximation_ratio
                except (ValueError, TypeError):
                    pass

    # Baseline comparisons (optional but implemented)
    if baseline and isinstance(baseline.get("metrics"), dict):
        b = baseline["metrics"]
        if "qc.quality.success_probability" in metrics and "qc.quality.success_probability" in b:
            delta = metrics["qc.quality.success_probability"] - b["qc.quality.success_probability"]
            metrics["qc.delta.success_probability"] = delta

    # Generate insights from metrics
    if "qc.quality.success_probability" in metrics:
        success_prob = metrics["qc.quality.success_probability"]
        if success_prob < 0.3:
            insights.append({
                "summary": f"Very low success probability ({success_prob:.1%}). Circuit may need significant optimization.",
                "severity": "critical"
            })
        elif success_prob < 0.5:
            insights.append({
                "summary": f"Low success probability ({success_prob:.1%}). Consider reviewing circuit design or increasing shots.",
                "severity": "warn"
            })
        elif success_prob > 0.9:
            insights.append({
                "summary": f"High success probability ({success_prob:.1%}). Circuit is performing well.",
                "severity": "info"
            })
    
    if "qc.transpile.depth_inflation_ratio" in metrics:
        inflation = metrics["qc.transpile.depth_inflation_ratio"]
        if inflation > 3.0:
            insights.append({
                "summary": f"Very high depth inflation ({inflation:.2f}x). Transpilation is significantly increasing circuit depth.",
                "severity": "warn"
            })
        elif inflation > 2.0:
            insights.append({
                "summary": f"Significant depth inflation ({inflation:.2f}x). Transpilation may be adding overhead.",
                "severity": "warn"
            })
    
    if "qc.time.queue_ms" in metrics and metrics["qc.time.queue_ms"] > 60000:
        insights.append({
            "summary": f"Long queue time ({metrics['qc.time.queue_ms']/1000:.1f}s). Backend may be heavily loaded.",
            "severity": "warn"
        })
    
    if "qc.cost.estimated_usd" in metrics and metrics["qc.cost.estimated_usd"] and metrics["qc.cost.estimated_usd"] > 1.0:
        insights.append({
            "summary": f"High estimated cost (${metrics['qc.cost.estimated_usd']:.4f}). Consider optimizing circuit or reducing shots.",
            "severity": "warn"
        })
    
    # Energy-based insights (for optimization problems)
    if "qc.optimization.energy" in metrics:
        energy = metrics["qc.optimization.energy"]
        if "qc.optimization.approximation_ratio" in metrics:
            ratio = metrics["qc.optimization.approximation_ratio"]
            if ratio <= 1.01:  # Within 1% of ground state
                insights.append({
                    "summary": f"Excellent solution found! Energy ({energy:.4f}) is very close to ground state (approximation ratio: {ratio:.4f}).",
                    "severity": "info"
                })
            elif ratio <= 1.1:  # Within 10% of ground state
                insights.append({
                    "summary": f"Good solution found. Energy ({energy:.4f}) is close to ground state (approximation ratio: {ratio:.4f}).",
                    "severity": "info"
                })
            elif ratio > 2.0:  # More than 2x ground state
                insights.append({
                    "summary": f"Solution quality could be improved. Energy ({energy:.4f}) is {ratio:.2f}x the ground state. Consider adjusting solver parameters or annealing schedule.",
                    "severity": "warn"
                })
        else:
            # No ground state for comparison, just report energy
            insights.append({
                "summary": f"Optimization solution found with energy: {energy:.4f}.",
                "severity": "info"
            })

    return {"metrics": metrics, "insights": insights, "pack_versions": {"collector": "0.1.0"}}
