import { useState } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import CodeBlock from './CodeBlock';

interface Props {
  options: Record<string, any>;
}

/** Everything the job was submitted with apart from its circuits (IBM's "Input options"). */
export default function InputOptions({ options }: Props) {
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between text-left">
        <h3 className="text-lg font-semibold text-white">Input Options</h3>
        {open ? <ChevronUp className="text-dark-text-muted" /> : <ChevronDown className="text-dark-text-muted" />}
      </button>
      {open && (
        <div className="mt-4">
          <p className="text-sm text-dark-text-muted mb-3">
            The options the job was submitted with, as the provider received them.
          </p>
          <CodeBlock text={JSON.stringify(options, null, 2)} />
        </div>
      )}
    </div>
  );
}
