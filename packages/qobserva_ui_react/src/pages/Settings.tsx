import { useQuery } from '@tanstack/react-query';
import { apiService } from '../services/api';
import { FolderOpen, Info } from 'lucide-react';
import logoImage from '../assets/images/qoblogo.png';

export default function Settings() {
  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => apiService.getSettings(),
  });

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold text-white">Settings</h1>
        <img 
          src={logoImage} 
          alt="QObserva Logo" 
          className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
        />
      </div>
      
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white flex items-center gap-2">
          <FolderOpen className="w-5 h-5" />
          Data Directory
        </h3>
        
        {isLoading ? (
          <p className="text-dark-text-muted">Loading...</p>
        ) : settings ? (
          <div className="space-y-4">
            <div>
              <p className="text-sm text-dark-text-muted mb-2">Current Data Directory:</p>
              <div className="bg-dark-bg border border-dark-border rounded-lg p-3 font-mono text-sm text-dark-text break-all">
                {settings.data_dir}
              </div>
              {settings.data_dir === '/data' && (
                <p className="text-xs text-primary mt-2">
                  🐳 Running in <strong>Docker mode</strong> - data stored in Docker volume
                </p>
              )}
            </div>
            
            <div className="bg-dark-bg/50 border border-dark-border rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Info className="w-5 h-5 text-primary mt-0.5 flex-shrink-0" />
                <div className="space-y-2 text-sm text-dark-text-muted">
                  {settings.data_dir === '/data' ? (
                    // Docker mode
                    <>
                      <p className="text-dark-text font-medium">Docker Mode: Data in Docker Volume</p>
                      <p className="text-xs">Data is stored in a Docker volume named <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">docker_qobserva_data</code>.</p>
                      <p className="text-dark-text font-medium mt-3">How to Access Data:</p>
                      <ol className="list-decimal list-inside space-y-1 ml-2">
                        <li>View volume location: <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">docker volume inspect docker_qobserva_data</code></li>
                        <li>Access from container: <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">docker exec -it docker-collector-1 ls -la /data</code></li>
                        <li>Copy files out: <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">docker cp docker-collector-1:/data/qobserva.sqlite3 ./</code></li>
                      </ol>
                      <p className="text-dark-text font-medium mt-3">How to Change Data Directory (Docker):</p>
                      <ol className="list-decimal list-inside space-y-1 ml-2">
                        <li>Edit <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">docker/docker-compose.yml</code> and update the volume mount</li>
                        <li>Or set <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">QOBSERVA_DATA_DIR</code> in the environment section</li>
                        <li>Restart: <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">make docker-down && make docker-up</code></li>
                      </ol>
                    </>
                  ) : (
                    // Native mode
                    <>
                      <p className="text-dark-text font-medium">How to Change Data Directory:</p>
                      <ol className="list-decimal list-inside space-y-1 ml-2">
                        <li>Set the <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">QOBSERVA_DATA_DIR</code> environment variable to your desired path</li>
                        <li>Stop QObserva: <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">qobserva down</code></li>
                        <li>Start QObserva: <code className="bg-dark-bg px-1.5 py-0.5 rounded text-primary">qobserva up</code></li>
                      </ol>
                    </>
                  )}
                  <p className="text-xs mt-3 pt-3 border-t border-dark-border">
                    <strong>Note:</strong> The data directory cannot be changed at runtime. 
                    All runs, database, and artifacts are stored in this directory.
                  </p>
                </div>
              </div>
            </div>

            <div className="mt-4 pt-4 border-t border-dark-border">
              <p className="text-xs text-dark-text-muted mb-2">Data Structure:</p>
              <div className="bg-dark-bg border border-dark-border rounded-lg p-3 font-mono text-xs text-dark-text">
                <div>{settings.data_dir}/</div>
                <div className="ml-4">├── qobserva.sqlite3 <span className="text-dark-text-muted">(database)</span></div>
                <div className="ml-4">└── artifacts/</div>
                <div className="ml-8">├── {`{project}/`}</div>
                <div className="ml-12">└── {`{run_id}/`}</div>
                <div className="ml-16">├── event.json</div>
                <div className="ml-16">└── analysis.json</div>
              </div>
            </div>
          </div>
        ) : (
          <p className="text-dark-text-muted">Unable to load settings.</p>
        )}
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4 text-white">About</h3>
        <div className="space-y-2 text-sm text-dark-text-muted">
          <p><strong className="text-dark-text">QObserva v{settings?.qobserva_version || 'unknown'}</strong></p>
          <p>Local-first observability and benchmarking for quantum program executions.</p>
          <p className="text-xs">
            Components: agent v{settings?.qobserva_agent_version || 'unknown'} | collector v{settings?.qobserva_collector_version || 'unknown'} | local v{settings?.qobserva_local_version || 'unknown'}
          </p>
          <ul className="list-disc list-inside space-y-1 mt-4">
            <li>Standardized run telemetry</li>
            <li>Metrics and insights generation</li>
            <li>Multi-SDK support (Qiskit, Braket, Cirq, PennyLane, pyQuil, D-Wave)</li>
          </ul>
        </div>
      </div>
    </div>
  );
}
