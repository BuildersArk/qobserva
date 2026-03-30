/**
 * Tag-aware warnings for run details
 * 
 * Conservative approach: Only warn on clearly test/error-related tags
 * to avoid false assumptions about user data.
 */

export interface TagWarning {
  severity: 'info' | 'warn';
  message: string;
  tagContext?: string; // Which tag triggered the warning
}

/**
 * Check tags for test/error-related patterns and generate warnings if appropriate
 * 
 * This is conservative - only warns on clearly test/error scenarios:
 * - error_test algorithm tags
 * - error_type tags (indicates intentional error scenarios)
 * - test tags with "error" in the value
 * 
 * Does NOT warn on normal test tags like "test": "entanglement" or "algorithm": "grover"
 */
export function checkTagWarnings(tags: Record<string, string> | undefined): TagWarning | null {
  if (!tags || Object.keys(tags).length === 0) {
    return null;
  }

  // Pattern 1: algorithm: "error_test" - clearly indicates error testing
  if (tags.algorithm === 'error_test') {
    const errorType = tags.error_type || 'error scenario';
    return {
      severity: 'warn',
      message: `This run is tagged as an error test (${errorType}). Results may not represent normal execution and should be interpreted accordingly.`,
      tagContext: `algorithm: error_test, error_type: ${errorType}`,
    };
  }

  // Pattern 2: error_type tag exists (indicates intentional error scenario)
  // Only warn if it's clearly an error test, not just any tag with "error" in the name
  if (tags.error_type && tags.error_type !== 'none' && tags.error_type !== '') {
    // Check if this is part of a test scenario
    const isTestScenario = tags.algorithm === 'error_test' || 
                          tags.test?.toLowerCase().includes('error') ||
                          tags.purpose?.toLowerCase().includes('error') ||
                          tags.scenario?.toLowerCase().includes('error');
    
    if (isTestScenario) {
      return {
        severity: 'warn',
        message: `This run is tagged with error_type: "${tags.error_type}". This appears to be an intentional error test scenario - results may not be meaningful for normal analysis.`,
        tagContext: `error_type: ${tags.error_type}`,
      };
    }
  }

  // Pattern 3: test tag with "error" in value (case-insensitive)
  if (tags.test && tags.test.toLowerCase().includes('error')) {
    return {
      severity: 'info',
      message: `This run is tagged as a test with "error" in the tag value. Results may be from an error handling test scenario.`,
      tagContext: `test: ${tags.test}`,
    };
  }

  // Pattern 4: purpose/scenario tags indicating error testing
  const purpose = tags.purpose?.toLowerCase() || '';
  const scenario = tags.scenario?.toLowerCase() || '';
  
  if ((purpose.includes('error') || scenario.includes('error')) && 
      (purpose.includes('test') || scenario.includes('test'))) {
    return {
      severity: 'info',
      message: `This run appears to be an error test scenario based on tags. Results should be interpreted in that context.`,
      tagContext: purpose ? `purpose: ${tags.purpose}` : `scenario: ${tags.scenario}`,
    };
  }

  // No warning needed - tags don't indicate test/error scenarios
  return null;
}
