interface Props {
  value: number;
  label: string;
  max?: number;
}

export default function GaugeChart({ value, label, max = 100 }: Props) {
  const percentage = Math.min((value / max) * 100, 100);
  const circumference = 2 * Math.PI * 90; // radius = 90
  const strokeDasharray = circumference;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getColor = () => {
    if (percentage >= 70) return '#10b981';
    if (percentage >= 40) return '#f59e0b';
    return '#ef4444';
  };

  return (
    <div className="flex flex-col items-center justify-center">
      <div className="relative">
        <svg width="200" height="200" className="transform -rotate-90">
          {/* Background circle */}
          <circle
            cx="100"
            cy="100"
            r="90"
            fill="none"
            stroke="#334155"
            strokeWidth="12"
          />
          {/* Progress circle */}
          <circle
            cx="100"
            cy="100"
            r="90"
            fill="none"
            stroke={getColor()}
            strokeWidth="12"
            strokeDasharray={strokeDasharray}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className="transition-all duration-500"
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-4xl font-bold text-white">{value.toFixed(1)}</div>
          <div className="text-sm text-dark-text-muted">{label}</div>
        </div>
      </div>
    </div>
  );
}
