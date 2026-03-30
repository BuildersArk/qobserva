import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import logoImage from '../assets/images/qoblogo.png';

type ReportType = 'executive' | 'provider_backend' | 'quality_anomaly';

function buildReportUrl(type: ReportType, filters: { project?: string; startDate?: string; endDate?: string }) {
  const params = new URLSearchParams();
  params.set('type', type);
  if (filters.project) params.set('project', filters.project);
  if (filters.startDate) params.set('startDate', filters.startDate);
  if (filters.endDate) params.set('endDate', filters.endDate);
  return `/report?${params.toString()}`;
}

export default function Reports() {
  const navigate = useNavigate();
  const [type, setType] = useState<ReportType>('executive');
  const [project, setProject] = useState<string>('');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const requirements = useMemo(() => {
    return {
      required: ['Date range (start + end)'],
      optional: ['Project'],
      notUsed: ['Provider', 'Status (reports are intentionally general)'],
    };
  }, []);

  const canGenerate = Boolean(startDate && endDate);

  const openReport = () => {
    const url = buildReportUrl(type, {
      project: project || undefined,
      startDate: startDate ? new Date(startDate + 'T00:00:00Z').toISOString().replace(/\.\d{3}Z$/, 'Z') : undefined,
      endDate: endDate ? new Date(endDate + 'T23:59:59Z').toISOString().replace(/\.\d{3}Z$/, 'Z') : undefined,
    });
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h1 className="text-3xl font-bold text-white">Generate Report</h1>
          <img 
            src={logoImage} 
            alt="QObserva Logo" 
            className="h-20 w-20 sm:h-24 sm:w-24 md:h-28 md:w-28 lg:h-32 lg:w-32 xl:h-36 xl:w-36 object-contain flex-shrink-0"
          />
        </div>
        <p className="text-dark-text-muted">
          Generate a PDF via browser print. Choose a report type, set filters, then print/save as PDF.
        </p>
      </div>

      <div className="card space-y-6">
        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-dark-text-muted mb-2">Report Type</label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value as ReportType)}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm"
            >
              <option value="executive">Executive Summary</option>
              <option value="provider_backend">Provider/Backend Performance</option>
              <option value="quality_anomaly">Run Quality / Anomaly</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-semibold text-dark-text-muted mb-2">Project (optional)</label>
            <input
              value={project}
              onChange={(e) => setProject(e.target.value)}
              placeholder="e.g. pennylane_test"
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm"
            />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-6">
          <div>
            <label className="block text-sm font-semibold text-dark-text-muted mb-2">Start Date (required)</label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              style={{ colorScheme: 'light' }}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm qobserva-date-input"
            />
          </div>
          <div>
            <label className="block text-sm font-semibold text-dark-text-muted mb-2">End Date (required)</label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              style={{ colorScheme: 'light' }}
              className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm qobserva-date-input"
            />
          </div>
        </div>

        <div className="bg-dark-bg border border-dark-border rounded-lg p-4">
          <div className="text-sm font-semibold text-white mb-2">Requirements</div>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-dark-text-muted mb-1">Required</div>
              <ul className="space-y-1 text-dark-text">
                {requirements.required.map((r) => (
                  <li key={r}>- {r}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-dark-text-muted mb-1">Optional</div>
              <ul className="space-y-1 text-dark-text">
                {requirements.optional.map((r) => (
                  <li key={r}>- {r}</li>
                ))}
              </ul>
            </div>
            <div>
              <div className="text-dark-text-muted mb-1">Not used</div>
              <ul className="space-y-1 text-dark-text">
                {requirements.notUsed.map((r) => (
                  <li key={r}>- {r}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button onClick={() => navigate(-1)} className="btn-secondary">
            Back
          </button>
          <button onClick={openReport} disabled={!canGenerate} className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed">
            Open Report (Print/PDF)
          </button>
          {!canGenerate && (
            <div className="text-sm text-dark-text-muted">Select start + end date to enable report generation.</div>
          )}
        </div>
      </div>
    </div>
  );
}

