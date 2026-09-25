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
  // Present when requested with includeSummary (collector 0.1.5+)
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
  execution: {
    status: string;
    shots: number;
    runtime_ms?: number;
    queue_ms?: number;
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
  };
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
