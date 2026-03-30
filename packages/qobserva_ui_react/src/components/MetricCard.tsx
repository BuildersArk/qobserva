// MetricCard component

interface MetricCardProps {
  label: string;
  value: string;
  change?: string;
  onClick?: () => void;
  clickable?: boolean;
}

export default function MetricCard({ label, value, change, onClick, clickable = false }: MetricCardProps) {
  const handleClick = () => {
    if (clickable && onClick) {
      onClick();
    }
  };

  return (
    <div 
      className={`metric-card ${clickable ? 'cursor-pointer hover:border-primary/50 transition-colors' : ''}`}
      onClick={handleClick}
    >
      <div className="text-xs font-semibold text-dark-text-muted uppercase tracking-wide mb-2">
        {label}
      </div>
      <div className="text-3xl font-bold text-white">{value}</div>
      {change && (
        <div className="text-xs text-dark-text-muted mt-2">{change}</div>
      )}
    </div>
  );
}
