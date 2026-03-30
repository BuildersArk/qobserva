import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer, Legend, Tooltip } from 'recharts';
import { Run } from '../../services/api';

interface Props {
  runs: Run[];
  onSliceClick?: (status: string) => void;
}

const COLORS = {
  success: '#10b981',
  failed: '#ef4444',
  cancelled: '#6b7280',
  default: '#3b82f6',
};

export default function StatusDistribution({ runs, onSliceClick }: Props) {
  const navigate = useNavigate();
  
  const data = useMemo(() => {
    const statusCounts = runs.reduce((acc, run) => {
      acc[run.status] = (acc[run.status] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    return Object.entries(statusCounts).map(([status, count]) => ({
      name: status.charAt(0).toUpperCase() + status.slice(1),
      value: count,
      status: status,
      color: COLORS[status as keyof typeof COLORS] || COLORS.default,
    }));
  }, [runs]);

  const handleClick = (data: any) => {
    // Recharts passes the data entry directly
    if (data && data.status) {
      if (onSliceClick) {
        onSliceClick(data.status);
      } else {
        // Navigate to filtered view
        navigate(`/?status=${data.status}`);
      }
    }
  };

  if (data.length === 0) {
    return <div className="text-center py-12 text-dark-text-muted">No data available</div>;
  }

  // Calculate total to determine if we need padding
  const total = data.reduce((sum, d) => sum + d.value, 0);
  const hasMultipleSlices = data.length > 1;
  
  // Custom label renderer to show count on pie slices
  const renderLabel = (entry: any) => {
    return `${entry.name}: ${entry.value}`;
  };

  // Custom tooltip to show count and percentage
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percentage = total > 0 ? ((data.value / total) * 100).toFixed(1) : 0;
      
      return (
        <div className="bg-dark-surface border border-dark-border rounded-lg p-3 shadow-lg">
          <p className="text-white font-semibold">{data.name}</p>
          <p className="text-dark-text-muted text-sm">
            Count: <span className="text-white font-medium">{data.value}</span>
          </p>
          <p className="text-dark-text-muted text-sm">
            Percentage: <span className="text-white font-medium">{percentage}%</span>
          </p>
        </div>
      );
    }
    return null;
  };

  return (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={hasMultipleSlices ? 2 : 0}
          dataKey="value"
          onClick={handleClick}
          style={{ cursor: 'pointer' }}
          label={renderLabel}
          labelLine={false}
        >
          {data.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ color: '#e2e8f0' }}
          iconType="circle"
          formatter={(value: string, entry: any) => {
            const percentage = total > 0 ? ((entry.payload.value / total) * 100).toFixed(1) : 0;
            return `${value} (${entry.payload.value}, ${percentage}%)`;
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
