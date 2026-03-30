import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Home from './pages/Home';
import RunDetails from './pages/RunDetails';
import Compare from './pages/Compare';
import Analytics from './pages/Analytics';
import Algorithms from './pages/Algorithms';
import Settings from './pages/Settings';
import FilteredRuns from './pages/FilteredRuns';
import SearchRuns from './pages/SearchRuns';
import Reports from './pages/Reports';
import ReportPrint from './pages/ReportPrint';

function App() {
  const [filters, setFilters] = useState<{
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
    algorithm?: string;
  }>({});

  const handleFilterChange = (newFilters: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
    algorithm?: string;
  }) => {
    setFilters(newFilters);
  };

  return (
    <BrowserRouter>
      <Layout onFilterChange={handleFilterChange}>
            <Routes>
              <Route path="/" element={<Home filters={filters} />} />
              <Route path="/search" element={<SearchRuns />} />
              <Route path="/runs/:runId" element={<RunDetails />} />
              <Route path="/runs-filtered" element={<FilteredRuns />} />
              <Route path="/compare" element={<Compare />} />
              <Route path="/analytics" element={<Analytics filters={filters} />} />
              <Route path="/algorithms" element={<Algorithms filters={filters} />} />
              <Route path="/reports" element={<Reports />} />
              <Route path="/report" element={<ReportPrint />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
