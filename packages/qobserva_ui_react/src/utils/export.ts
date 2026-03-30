/**
 * Export data to CSV file
 */
export function exportToCSV(data: any[], filename: string) {
  if (data.length === 0) {
    alert('No data to export');
    return;
  }

  // Get headers from first object
  const headers = Object.keys(data[0]);
  
  // Create CSV content
  const csvContent = [
    // Header row
    headers.join(','),
    // Data rows
    ...data.map(row => 
      headers.map(header => {
        const value = row[header];
        // Handle values that might contain commas, quotes, or newlines
        if (value === null || value === undefined) {
          return '';
        }
        const stringValue = String(value);
        // Escape quotes and wrap in quotes if contains comma, quote, or newline
        if (stringValue.includes(',') || stringValue.includes('"') || stringValue.includes('\n')) {
          return `"${stringValue.replace(/"/g, '""')}"`;
        }
        return stringValue;
      }).join(',')
    )
  ].join('\n');

  // Create blob and download
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const link = document.createElement('a');
  const url = URL.createObjectURL(blob);
  
  link.setAttribute('href', url);
  link.setAttribute('download', `${filename}.csv`);
  link.style.visibility = 'hidden';
  
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  URL.revokeObjectURL(url);
}

/**
 * Export runs data to CSV
 */
export function exportRunsToCSV(runs: any[], filename: string = 'qobserva-runs') {
  const exportData = runs.map(run => ({
    'Run ID': run.run_id,
    'Time': new Date(run.created_at).toISOString(),
    'Project': run.project,
    'Provider': run.provider,
    'Backend': run.backend_name,
    'Status': run.status,
    'Shots': run.shots,
  }));
  
  exportToCSV(exportData, filename);
}

/**
 * Export backend stats to CSV
 */
export function exportBackendsToCSV(backendStats: any[], filename: string = 'qobserva-backends') {
  const exportData = backendStats.map(backend => ({
    'Backend Name': backend.backend_name,
    'Provider': backend.provider,
    'Total Runs': backend.total,
    'Success': backend.success,
    'Failed': backend.failed,
    'Cancelled': backend.cancelled,
    'Success Rate (%)': backend.total > 0 ? ((backend.success / backend.total) * 100).toFixed(2) : '0.00',
  }));
  
  exportToCSV(exportData, filename);
}
