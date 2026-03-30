import { useState, useEffect, useRef } from 'react';
import { Calendar, X } from 'lucide-react';

interface Props {
  onDateRangeChange?: (startDate?: string, endDate?: string) => void;
  initialStartDate?: string; // YYYY-MM-DD format
  initialEndDate?: string; // YYYY-MM-DD format
}

export default function DateRangePicker({ onDateRangeChange, initialStartDate, initialEndDate }: Props) {
  const [showPicker, setShowPicker] = useState(true); // Show by default when Custom is selected
  const [startDate, setStartDate] = useState(initialStartDate || '');
  const [endDate, setEndDate] = useState(initialEndDate || '');
  const pickerRef = useRef<HTMLDivElement>(null);

  // Update local state when initial values change
  useEffect(() => {
    if (initialStartDate !== undefined) {
      setStartDate(initialStartDate);
    }
    if (initialEndDate !== undefined) {
      setEndDate(initialEndDate);
    }
  }, [initialStartDate, initialEndDate]);

  // Close picker when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowPicker(false);
      }
    };

    if (showPicker) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showPicker]);

  const handleApply = () => {
    if (startDate && endDate) {
      // Validate that end date is after start date
      if (new Date(endDate) >= new Date(startDate)) {
        onDateRangeChange?.(startDate, endDate);
        setShowPicker(false);
      } else {
        alert('End date must be after start date');
      }
    } else if (startDate || endDate) {
      alert('Please select both start and end dates');
    }
  };

  const handleClear = () => {
    setStartDate('');
    setEndDate('');
    onDateRangeChange?.(undefined, undefined);
    setShowPicker(false);
  };

  // Get today's date in YYYY-MM-DD format for max attribute
  const today = new Date().toISOString().split('T')[0];

  return (
    <div className="relative" ref={pickerRef}>
      <button
        onClick={() => setShowPicker(!showPicker)}
        className="bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm flex items-center gap-2 hover:border-primary/50 transition-colors"
      >
        <Calendar size={16} />
        {startDate && endDate ? (
          <span className="text-xs">
            {new Date(startDate).toLocaleDateString()} - {new Date(endDate).toLocaleDateString()}
          </span>
        ) : (
          <span>Select Dates</span>
        )}
      </button>
      
      {showPicker && (
        <div className="absolute top-full mt-2 right-0 bg-dark-surface border border-dark-border rounded-lg p-4 shadow-xl z-50 min-w-[320px]">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-white">Select Date Range</h3>
            <button
              onClick={() => setShowPicker(false)}
              className="text-dark-text-muted hover:text-dark-text transition-colors"
            >
              <X size={18} />
            </button>
          </div>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-dark-text-muted mb-2">
                Start Date
              </label>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                max={endDate || today}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm focus:outline-none focus:border-primary/50 transition-colors"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-dark-text-muted mb-2">
                End Date
              </label>
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                min={startDate || undefined}
                max={today}
                className="w-full bg-dark-bg border border-dark-border rounded-lg px-3 py-2 text-dark-text text-sm focus:outline-none focus:border-primary/50 transition-colors"
              />
            </div>
            <div className="flex gap-2 pt-2">
              <button
                onClick={handleApply}
                className="flex-1 bg-primary hover:bg-primary/90 text-white text-sm py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                disabled={!startDate || !endDate}
              >
                Apply
              </button>
              <button
                onClick={handleClear}
                className="px-4 py-2 bg-dark-bg border border-dark-border hover:bg-dark-bg/80 text-dark-text text-sm rounded-lg transition-colors"
              >
                Clear
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
