import { useState } from 'react';
import { Copy, Check } from 'lucide-react';

interface Props {
  text: string;
  maxHeight?: number;
  note?: string;
}

/** Monospace block with a copy button, for QASM, circuit diagrams, options and code snippets. */
export default function CodeBlock({ text, maxHeight = 360, note }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={copy}
        className="absolute top-2 right-2 p-1.5 rounded bg-dark-surface hover:bg-dark-border text-dark-text-muted hover:text-primary"
        title="Copy to clipboard"
      >
        {copied ? <Check size={14} className="text-success" /> : <Copy size={14} />}
      </button>
      <pre
        className="bg-dark-bg border border-dark-border rounded p-4 pr-12 text-xs text-dark-text font-mono overflow-auto whitespace-pre"
        style={{ maxHeight }}
      >
        {text}
      </pre>
      {note && <p className="text-xs text-dark-text-muted mt-2">{note}</p>}
    </div>
  );
}
