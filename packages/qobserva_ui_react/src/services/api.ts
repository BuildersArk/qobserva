import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Run {
  run_id: string;
  event_id: string;
  created_at: string;
  project: string;
  provider: string;
  backend_name: string;
  status: string;
  shots: number;
  // Sent with every run by collector 0.1.6+ (algorithm also with includeSummary on 0.1.5)
  sdk?: string | null;
  job_id?: string | null;
  algorithm?: string | null;
  summary?: RunSummary | null;
}

// Per-run fields the dashboard aggregates across many runs, served with the run list
// so charts don't have to fetch every run's event and analysis.
export interface RunSummary {
  sdk?: string | null;
  runtime_ms?: number | null;
  metrics: Record<string, number>;
  benchmark_params: Record<string, number>;
}

export interface Algorithm {
  name: string;
  count: number;
}

export interface Metric {
  [key: string]: any;
}

export interface Analysis {
  metrics: Metric;
  insights: Array<{
    summary: string;
    severity: 'info' | 'warn' | 'critical';
  }>;
}

export interface Event {
  event_id?: string;
  run_id: string;
  created_at?: string;
  project: string;
  tags?: Record<string, string>;
  backend: {
    provider: string;
    name: string;
  };
  software?: {
    qobserva_version?: string;
    agent_version?: string;
    collector_version?: string;
    sdk?: {
      name?: string;
      version?: string;
    };
    python_version?: string;
  };
  program?: {
    circuit_metrics?: CircuitMetrics;
    circuit?: CircuitText;
    [key: string]: any;
  };
  execution: {
    status: string;
    shots: number;
    exact?: boolean;
    runtime_ms?: number;
    queue_ms?: number;
    timeline?: {
      created?: string;
      running?: string;
      finished?: string;
      source?: string;
    };
    execution_spans?: {
      count: number;
      total_s: number;
      start?: string;
      stop?: string;
      spans?: Array<{ start: string; stop: string; duration_s: number }>;
    };
    chunk_timing?: {
      count: number;
      total_s: number;
      chunks: Array<{ start: string; stop: string; duration_s: number; parts?: Array<{ item: number; size: number }> }>;
    };
    options?: Record<string, any>;
    input_options?: Record<string, any>;
    provider_job?: ProviderJob;
    resource_usage?: Record<string, any>;
  };
  artifacts: {
    result_type?: string;
    counts?: {
      histogram: Record<string, number>;
    };
    energies?: {
      value?: number | null;
      stderr?: number | null;
    };
    expectations?: ExpectationArtifact[];
    probabilities?: {
      values: Record<string, number>;
      truncated?: boolean;
    };
    batches?: BatchArtifact[];
    annealing?: AnnealingArtifact;
    unrecognized?: { type?: string };
    pending_job?: { type?: string; job_id?: string | null };
  };
}

export interface ProviderJob {
  job_id: string;
  provider?: string;
  program?: string;
  mode?: string;
  session_id?: string;
  tags?: string[];
  items?: number;
  region?: string;
  created?: string;
  usage_estimate_s?: number;
  private?: boolean;
  label?: string;
  problem_data_id?: string;
  device?: string;
  arn?: string;
  // Google Quantum Engine / Quantum Virtual Machine (cirq_google)
  processor?: string;
  program_id?: string;
  status?: string;
  updated?: string;
  calibration?: string;
  virtual?: boolean;
}

export interface CircuitText {
  format?: string; // openqasm3 | openqasm2 | quil
  source?: { text: string; truncated?: boolean; full_length?: number };
  diagram?: { text: string; truncated?: boolean; full_length?: number };
  diagram_omitted?: string;
  from?: string; // decorator | job | qnode
}

export interface CircuitMetrics {
  num_qubits?: number;
  depth_pre?: number;
  depth_post?: number;
  two_qubit_gate_count_pre?: number;
  two_qubit_gate_count_post?: number;
  gate_counts?: Record<string, number>;
  source?: string;
}

export interface ExpectationArtifact {
  operator: string;
  value: number;
  stderr?: number | null;
  kind?: string;
}

export interface BatchArtifact {
  label?: string;
  params?: Record<string, number | string>;
  shots?: number;
  histogram: Record<string, number>;
}

export interface AnnealingArtifact {
  chain_break_fraction?: number;
  max_chain_break_fraction?: number;
  num_logical_variables?: number;
  num_physical_qubits?: number;
  max_chain_length?: number;
  mean_chain_length?: number;
  chain_strength?: number;
  chain_break_method?: string;
}

export const apiService = {
  // List runs
  getRuns: async (params?: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
    algorithm?: string;
    limit?: number;
    includeSummary?: boolean;
  }): Promise<Run[]> => {
    // Convert camelCase to snake_case for backend API
    const apiParams: any = {};
    if (params?.project) apiParams.project = params.project;
    if (params?.provider) apiParams.provider = params.provider;
    if (params?.status) apiParams.status = params.status;
    if (params?.startDate) {
      // Ensure startDate is in ISO format for backend comparison
      apiParams.start_date = params.startDate;
    }
    if (params?.endDate) {
      // Ensure endDate is in ISO format for backend comparison
      apiParams.end_date = params.endDate;
    }
    if (params?.algorithm) apiParams.algorithm = params.algorithm;
    if (params?.limit) apiParams.limit = params.limit;
    if (params?.includeSummary) apiParams.include_summary = true;

    const response = await api.get('/runs', { params: apiParams });
    return response.data;
  },

  // Get list of algorithms
  getAlgorithms: async (): Promise<Algorithm[]> => {
    const response = await api.get('/algorithms');
    return response.data.algorithms || [];
  },

  // Get run details
  getRun: async (project: string, runId: string): Promise<{
    event: Event;
    analysis: Analysis;
  }> => {
    // Try the project-specific endpoint first, fallback to simple run_id
    try {
      const [eventRes, analysisRes] = await Promise.all([
        api.get(`/runs/${project}/${runId}/event`),
        api.get(`/runs/${project}/${runId}/analysis`),
      ]);
      return {
        event: eventRes.data,
        analysis: analysisRes.data,
      };
    } catch (error) {
      // Fallback: try without project prefix
      const [eventRes, analysisRes] = await Promise.all([
        api.get(`/runs/${runId}`),
        api.get(`/runs/${runId}/analysis`),
      ]);
      return {
        event: eventRes.data,
        analysis: analysisRes.data,
      };
    }
  },

  // Health check
  health: async (): Promise<{ status: string }> => {
    const response = await api.get('/health');
    return response.data;
  },

  // Get settings
  getSettings: async (): Promise<{
    data_dir: string;
    data_dir_source: string;
    qobserva_version?: string;
    qobserva_agent_version?: string;
    qobserva_collector_version?: string;
    qobserva_local_version?: string;
  }> => {
    const response = await api.get('/settings');
    return response.data;
  },
};
