import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface Props {
  runId: string;
  truncate?: boolean;
  className?: string;
  showFullOnHover?: boolean;
}

export default function CopyableRunId({ 
  runId, 
  truncate = true, 
  className = '',
  showFullOnHover = false 
}: Props) {
  const [copied, setCopied] = useState(false);
  const [showFull, setShowFull] = useState(false);

  const handleCopy = async (e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent row click when copying
    try {
      await navigator.clipboard.writeText(runId);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const displayText = truncate && !showFull ? `${runId.substring(0, 12)}...` : runId;

  return (
    <div 
      className={`flex items-center gap-2 group ${className}`}
      onMouseEnter={() => showFullOnHover && setShowFull(true)}
      onMouseLeave={() => showFullOnHover && setShowFull(false)}
    >
      <span className="font-mono text-xs text-dark-text" title={runId}>
        {displayText}
      </span>
      <button
        onClick={handleCopy}
        className="opacity-0 group-hover:opacity-100 transition-opacity p-1 hover:bg-dark-bg rounded text-dark-text-muted hover:text-primary"
        title="Copy run ID to clipboard"
      >
        {copied ? (
          <Check size={14} className="text-success" />
        ) : (
          <Copy size={14} />
        )}
      </button>
    </div>
  );
}
