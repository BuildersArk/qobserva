import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { Run } from '../../services/api';

interface Props {
  runs: Run[];
}

const COLORS = {
  success: '#10b981',
  failed: '#ef4444',
  cancelled: '#6b7280',
  default: '#3b82f6',
};

export default function ShotsScatter({ runs }: Props) {
  const navigate = useNavigate();
  
  const data = useMemo(() => {
    return runs
      .sort((a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime())
      .map((run) => ({
        x: new Date(run.created_at).getTime(), // Use timestamp for X-axis
        y: run.shots,
        shots: run.shots,
        runId: run.run_id,
        status: run.status,
        project: run.project,
        backend: run.backend_name,
        createdAt: run.created_at,
        formattedDate: new Date(run.created_at).toLocaleString(),
      }));
  }, [runs]);

  const handleDotClick = (data: any) => {
    if (data && data.runId) {
      navigate(`/runs/${data.runId}`);
    }
  };

  // Custom tooltip component with better styling
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-dark-surface border border-primary/30 rounded-lg p-3 shadow-xl z-50 min-w-[200px]">
          <p className="text-white font-semibold mb-2">{data.formattedDate || new Date(data.createdAt).toLocaleString()}</p>
          <div className="space-y-1 text-sm">
            <p className="text-dark-text-muted">
              Shots: <span className="text-primary font-semibold">{data.shots.toLocaleString()}</span>
            </p>
            <p className="text-dark-text-muted">
              Status: <span className="text-white font-medium capitalize">{data.status}</span>
            </p>
            <p className="text-dark-text-muted">
              Backend: <span className="text-white font-medium">{data.backend}</span>
            </p>
            <p className="text-dark-text-muted">
              Project: <span className="text-white font-medium">{data.project}</span>
            </p>
            <p className="text-xs text-primary/70 mt-2 pt-2 border-t border-dark-border cursor-pointer">
              Click dot to view details
            </p>
          </div>
        </div>
      );
    }
    return null;
  };

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No shots data available</div>;
  }

  // Custom dot renderer with click handler and color coding - larger and more clickable
  const renderDot = (props: any): JSX.Element => {
    const { cx, cy, payload } = props;
    const fillColor = COLORS[payload?.status as keyof typeof COLORS] || COLORS.default;
    
    return (
      <g onClick={() => handleDotClick(payload)} style={{ cursor: 'pointer' }}>
        {/* Larger invisible hit area for easier clicking */}
        <circle
          cx={cx || 0}
          cy={cy || 0}
          r={10}
          fill="transparent"
          pointerEvents="all"
        />
        {/* Visible dot */}
        <circle
          cx={cx || 0}
          cy={cy || 0}
          r={6}
          fill={fillColor}
          stroke="#1e293b"
          strokeWidth={2}
          className="hover:r-7 hover:stroke-primary transition-all duration-150"
        />
      </g>
    );
  };

  return (
    <ResponsiveContainer width="100%" height={500}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
        <XAxis 
          type="number"
          dataKey="x"
          name="Time"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          domain={['dataMin', 'dataMax']}
          scale="time"
          tickFormatter={(value) => {
            return new Date(value).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
          }}
          label={{ value: 'Time', position: 'insideBottom', offset: -5, fill: '#94a3b8' }}
        />
        <YAxis 
          type="number"
          dataKey="y"
          name="Shots"
          stroke="#94a3b8"
          tick={{ fill: '#94a3b8', fontSize: 12 }}
          label={{ value: 'Shots', angle: -90, position: 'insideLeft', fill: '#94a3b8' }}
        />
        <Tooltip content={<CustomTooltip />} cursor={{ strokeDasharray: '3 3', stroke: '#3b82f6' }} />
        {/* Line connecting the dots */}
        <Line
          type="monotone"
          dataKey="shots"
          stroke="#3b82f6"
          strokeWidth={2}
          strokeOpacity={0.5}
          dot={renderDot}
          activeDot={{ 
            r: 8, 
            fill: '#3b82f6', 
            stroke: '#1e293b', 
            strokeWidth: 2,
            style: { cursor: 'pointer' }
          }}
          onClick={(data: any) => {
            if (data && data.payload) {
              handleDotClick(data.payload);
            }
          }}
          style={{ cursor: 'pointer' }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
