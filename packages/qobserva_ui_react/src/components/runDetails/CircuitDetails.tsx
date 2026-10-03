import { useState } from 'react';
import MetricCard from '../MetricCard';
import CodeBlock from './CodeBlock';
import type { CircuitMetrics, CircuitText } from '../../services/api';

interface Props {
  metrics?: CircuitMetrics;
  text?: CircuitText;
}

const SOURCE_TEXT: Record<string, string> = {
  decorator: 'from the circuit passed to @observe_run(circuit=...)',
  job: 'from the circuit the job ran',
  qnode: 'from the QNode at device level',
};

const FORMAT_LABEL: Record<string, string> = {
  openqasm3: 'OpenQASM 3',
  openqasm2: 'OpenQASM 2',
  quil: 'Quil',
};

function truncationNote(part?: { truncated?: boolean; full_length?: number }): string | undefined {
  return part?.truncated ? `Shortened for storage (full length ${part.full_length?.toLocaleString()} characters).` : undefined;
}

export default function CircuitDetails({ metrics = {}, text }: Props) {
  const executed = metrics.depth_post !== undefined;
  const depth = executed ? metrics.depth_post : metrics.depth_pre;
  const twoQ = executed ? metrics.two_qubit_gate_count_post : metrics.two_qubit_gate_count_pre;
  const gates = Object.entries(metrics.gate_counts || {}).sort(([, a], [, b]) => b - a);
  const totalGates = gates.reduce((sum, [, n]) => sum + n, 0);
  const source = metrics.source || text?.from;
  const hasMetrics = depth !== undefined || metrics.num_qubits !== undefined || gates.length > 0;

  const tabs: Array<{ key: string; label: string }> = [];
  if (text?.diagram || text?.diagram_omitted) tabs.push({ key: 'diagram', label: 'Diagram' });
  if (text?.source) tabs.push({ key: 'source', label: FORMAT_LABEL[text.format || ''] || 'Source' });
  const [tab, setTab] = useState(tabs[0]?.key);

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">Circuit</h3>
      <p className="text-sm text-dark-text-muted mb-4">
        {executed ? 'The circuit as executed' : 'The circuit as submitted (the device may compile it further)'}
        {source && SOURCE_TEXT[source] ? `, ${SOURCE_TEXT[source]}` : ''}.
        {hasMetrics && ' Two-qubit gates include larger multi-qubit gates; measurements and barriers are not counted as gates.'}
      </p>
      {hasMetrics && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {metrics.num_qubits !== undefined && <MetricCard label="Qubits" value={String(metrics.num_qubits)} />}
          {depth !== undefined && <MetricCard label="Depth" value={String(depth)} />}
          {twoQ !== undefined && <MetricCard label="Two-Qubit Gates" value={String(twoQ)} />}
          {gates.length > 0 && <MetricCard label="Total Gates" value={totalGates.toLocaleString()} />}
        </div>
      )}
      {gates.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-2">
          {gates.map(([name, n]) => (
            <span key={name} className="px-2 py-1 rounded text-xs font-semibold bg-primary/20 text-primary font-mono">
              {name} × {n.toLocaleString()}
            </span>
          ))}
        </div>
      )}
      {tabs.length > 0 && (
        <div className="mt-6">
          <div className="flex gap-2 mb-3">
            {tabs.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`px-3 py-1.5 rounded text-sm font-semibold ${
                  tab === t.key ? 'bg-primary/20 text-primary' : 'text-dark-text-muted hover:text-dark-text'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>
          {tab === 'diagram' && text?.diagram && (
            <CodeBlock text={text.diagram.text} note={truncationNote(text.diagram)} />
          )}
          {tab === 'diagram' && !text?.diagram && text?.diagram_omitted && (
            <p className="text-sm text-dark-text-muted">No diagram: {text.diagram_omitted}. The full circuit is in the source tab.</p>
          )}
          {tab === 'source' && text?.source && (
            <CodeBlock text={text.source.text} note={truncationNote(text.source)} />
          )}
        </div>
      )}
    </div>
  );
}
