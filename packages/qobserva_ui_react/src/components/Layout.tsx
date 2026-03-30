import { ReactNode } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Home, Search, GitCompare, BarChart3, Settings, FileText, Code2 } from 'lucide-react';
import FilterRibbon from './FilterRibbon';
import logoImage from '../assets/images/qoblogo.png';

interface LayoutProps {
  children: ReactNode;
  onFilterChange?: (filters: {
    project?: string;
    provider?: string;
    status?: string;
    startDate?: string;
    endDate?: string;
  }) => void;
}

const navItems = [
  { path: '/', icon: Home, label: 'Home' },
  { path: '/search', icon: Search, label: 'Search Runs' },
  { path: '/compare', icon: GitCompare, label: 'Compare' },
  { path: '/analytics', icon: BarChart3, label: 'Run Analytics' },
  { path: '/algorithms', icon: Code2, label: 'Algorithm Analytics' },
  { path: '/reports', icon: FileText, label: 'Generate Report' },
  { path: '/settings', icon: Settings, label: 'Settings' },
];

export default function Layout({ children, onFilterChange }: LayoutProps) {
  const location = useLocation();

  // Print-friendly route: render without sidebar/filter ribbon.
  const isReportPrint = location.pathname === '/report';
  
  // Disable filters on run details, compare, and search pages
  const isRunDetails = location.pathname.startsWith('/runs/');
  const isCompare = location.pathname === '/compare';
  const isSearch = location.pathname === '/search';
  const isAnalytics = location.pathname === '/analytics';
  const isAlgorithms = location.pathname === '/algorithms';
  const isReports = location.pathname === '/reports';
  const isSettings = location.pathname === '/settings';
  const filtersDisabled = isRunDetails || isCompare || isSearch || isReports || isSettings;

  if (isReportPrint) {
    return <div className="min-h-screen bg-white text-black">{children}</div>;
  }

  return (
    <div className="min-h-screen bg-dark-bg">
      {/* Sidebar */}
      <aside className="fixed left-0 top-0 h-screen w-80 bg-dark-surface border-r border-dark-border flex flex-col">
        <div className="p-6 border-b border-dark-border relative">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0 pr-3">
              <h1 className="text-2xl font-bold text-white leading-tight">QObserva</h1>
              <p className="text-sm text-dark-text-muted leading-tight mt-0.5 whitespace-nowrap">Quantum Observability</p>
            </div>
            <img 
              src={logoImage} 
              alt="QObserva Logo" 
              className="h-16 w-16 sm:h-20 sm:w-20 md:h-24 md:w-24 object-contain flex-shrink-0"
            />
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-2">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-primary/20 text-primary border border-primary/30'
                    : 'text-dark-text-muted hover:bg-dark-bg hover:text-dark-text'
                }`}
              >
                <Icon size={20} />
                <span className="font-medium">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </aside>

      {/* Main content */}
      <div className="ml-80">
        <FilterRibbon 
          onFilterChange={onFilterChange} 
          disabled={filtersDisabled}
          visible={
            isAnalytics 
              ? { project: true, provider: false, status: false, time: true, algorithm: false }
              : isAlgorithms
              ? { project: true, provider: true, status: true, time: true, algorithm: false }
              : undefined
          }
          showExport={!(isReports || isSettings || isAnalytics || isAlgorithms)}
          disabledMessage={isRunDetails
            ? "Filters are not available for individual run details"
            : isReports
            ? "Filters are not used on Generate Report (use the report inputs instead)"
            : isSettings
            ? "Filters are not used on Settings"
            : "Filters are not available for run comparisons"}
        />
        <main className="p-8">{children}</main>
      </div>
    </div>
  );
}
