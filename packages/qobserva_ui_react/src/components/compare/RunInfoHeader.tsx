import { useNavigate } from 'react-router-dom';
import { ExternalLink } from 'lucide-react';
import { Event } from '../../services/api';
import { format } from 'date-fns';
import CopyableRunId from '../CopyableRunId';

interface Props {
  event: Event;
  runId: string;
  label: string;
}

export default function RunInfoHeader({ event, runId, label }: Props) {
  const navigate = useNavigate();

  return (
    <div className="card">
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="text-lg font-semibold text-white">{label}</h3>
            <div className="flex items-center gap-2">
              <CopyableRunId runId={runId} />
              <button
                onClick={() => navigate(`/runs/${runId}`)}
                className="flex items-center gap-1 text-primary hover:text-primary/80 text-sm transition-colors"
                title="View run details"
              >
                <ExternalLink size={14} />
              </button>
            </div>
          </div>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <span className="text-dark-text-muted">Project:</span>
              <span className="text-dark-text ml-2 font-medium">{event.project}</span>
            </div>
            <div>
              <span className="text-dark-text-muted">Provider:</span>
              <span className="text-dark-text ml-2 font-medium">{event.backend.provider}</span>
            </div>
            <div>
              <span className="text-dark-text-muted">Backend:</span>
              <span className="text-dark-text ml-2 font-medium">{event.backend.name}</span>
            </div>
            <div>
              <span className="text-dark-text-muted">Time:</span>
              <span className="text-dark-text ml-2 font-medium">
                {event.created_at ? format(new Date(event.created_at), 'MMM dd, HH:mm') : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
