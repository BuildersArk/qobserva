import CopyableRunId from '../CopyableRunId';
import CodeBlock from './CodeBlock';
import type { Event, ProviderJob as ProviderJobInfo } from '../../services/api';

interface Props {
  job: ProviderJobInfo;
  execution: Event['execution'];
}

const TITLES: Record<string, string> = {
  ibm: 'IBM Quantum Job',
  dwave: 'D-Wave Problem',
  aws_braket: 'Amazon Braket Task',
  google: 'Google Quantum Engine Job',
};
const CONSOLES: Record<string, string> = {
  ibm: ' (IBM Quantum Platform → Workloads)',
  dwave: ' (D-Wave Leap)',
  aws_braket: ' (Amazon Braket console → Quantum tasks)',
};

function retrieveSnippet(job: ProviderJobInfo): string | null {
  if (job.provider === 'ibm') {
    return [
      'from qiskit_ibm_runtime import QiskitRuntimeService',
      '',
      '# Uses your saved IBM Quantum account',
      `job = QiskitRuntimeService().job("${job.job_id}")`,
      'result = job.result()',
    ].join('\n');
  }
  if (job.provider === 'dwave') {
    return [
      'from dwave.cloud import Client',
      '',
      '# Uses your saved D-Wave (Ocean) configuration',
      'with Client.from_config() as client:',
      `    sampleset = client.retrieve_answer("${job.job_id}").sampleset`,
    ].join('\n');
  }
  if (job.provider === 'aws_braket') {
    return [
      'from braket.aws import AwsQuantumTask',
      '',
      '# Uses your AWS credentials (e.g. AWS_PROFILE)',
      `task = AwsQuantumTask("${job.arn || job.job_id}")`,
      'result = task.result()',
    ].join('\n');
  }
  return null;
}

function Field({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex flex-col">
      <span className="text-dark-text-muted mb-1">{label}</span>
      <span className="text-dark-text font-medium">{value}</span>
    </div>
  );
}

export default function ProviderJob({ job, execution }: Props) {
  const billed = execution.resource_usage?.qpu_time_s;
  const execS = execution.resource_usage?.circuit_execution_time_s;
  const snippet = retrieveSnippet(job);

  const virtual = job.provider === 'google' && job.virtual;

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-2 text-white">
        {virtual ? 'Quantum Virtual Machine Job' : TITLES[job.provider || ''] || 'Provider Job'}
      </h3>
      {virtual ? (
        <p className="text-sm text-dark-text-muted mb-4">
          A local simulation of Google's {job.processor || 'processor'} with its published noise model (Cirq's Quantum
          Virtual Machine). The job ran on this computer; there is no cloud job.
        </p>
      ) : (
        <p className="text-sm text-dark-text-muted mb-4">
          The provider's own record of this run. Use the {job.provider === 'dwave' ? 'problem' : job.provider === 'aws_braket' ? 'task' : 'job'} ID to find it in the provider's console
          {CONSOLES[job.provider || ''] || ''}.
        </p>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div className="flex flex-col col-span-2">
          <span className="text-dark-text-muted mb-1">
            {job.provider === 'dwave' ? 'Problem ID' : job.provider === 'aws_braket' ? 'Quantum Task ID' : 'Job ID'}
          </span>
          <CopyableRunId runId={job.job_id} truncate={false} />
        </div>
        {job.program && <Field label="Program" value={job.program} />}
        {job.mode && <Field label="Mode" value={job.session_id ? `${job.mode} (${job.session_id})` : job.mode} />}
        {job.items !== undefined && <Field label="# of items" value={job.items} />}
        {job.arn && (
          <div className="flex flex-col col-span-2 md:col-span-4">
            <span className="text-dark-text-muted mb-1">Task ARN</span>
            <span className="text-dark-text font-medium font-mono break-all">{job.arn}</span>
          </div>
        )}
        {job.device && <Field label="Device" value={<span className="font-mono break-all">{job.device}</span>} />}
        {job.processor && <Field label="Processor" value={virtual ? `${job.processor} (virtual)` : job.processor} />}
        {job.status && <Field label="Status" value={job.status} />}
        {job.region && <Field label="Region" value={job.region} />}
        {job.created && <Field label="Created" value={new Date(job.created).toLocaleString()} />}
        {job.calibration && (
          <Field
            label={virtual ? 'Noise model calibration' : 'Calibration'}
            value={new Date(job.calibration).toLocaleString()}
          />
        )}
        {job.program_id && (
          <div className="flex flex-col col-span-2 md:col-span-4">
            <span className="text-dark-text-muted mb-1">Program ID</span>
            <span className="text-dark-text font-medium font-mono break-all">{job.program_id}</span>
          </div>
        )}
        {billed != null && (
          <Field
            label={job.provider === 'ibm' ? 'Usage (billed QPU)' : 'QPU access time'}
            value={`${job.provider === 'ibm' ? billed : Number(billed).toFixed(6)} s`}
          />
        )}
        {execS != null && (
          <Field
            label="Circuit execution (reported)"
            value={<span title="The provider's reported circuit execution time (IBM: circuits_execution_time_ns), not measured by QObserva">{`${Number(execS).toFixed(3)} s`}</span>}
          />
        )}
        {job.usage_estimate_s != null && <Field label="Usage estimate" value={`${job.usage_estimate_s} s`} />}
        {job.label && <Field label="Label" value={job.label} />}
        {execution.resource_usage?.charge_time_s != null && (
          <Field label="Charge time" value={`${Number(execution.resource_usage.charge_time_s).toFixed(3)} s`} />
        )}
        {execution.resource_usage?.run_time_s != null && (
          <Field label="Run time" value={`${Number(execution.resource_usage.run_time_s).toFixed(3)} s`} />
        )}
        {job.tags && job.tags.length > 0 && <Field label="Tags" value={job.tags.join(', ')} />}
      </div>
      {snippet && (
        <div className="mt-4">
          <span className="text-sm text-dark-text-muted">
            {job.provider === 'dwave' ? 'Retrieve this problem with Ocean'
              : job.provider === 'aws_braket' ? 'Retrieve this task with the Braket SDK' : 'Retrieve this job in Qiskit'}
          </span>
          <div className="mt-2">
            <CodeBlock text={snippet} maxHeight={160} />
          </div>
        </div>
      )}
    </div>
  );
}
