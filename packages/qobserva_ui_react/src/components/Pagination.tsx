import { ChevronLeft, ChevronRight } from 'lucide-react';

interface Props {
  page: number; // zero-based
  pageSize: number;
  total: number;
  onPageChange: (page: number) => void;
}

/** "Showing 51–92 of 92 runs" with Previous / Next. Renders nothing when everything fits on one page. */
export default function Pagination({ page, pageSize, total, onPageChange }: Props) {
  const pageCount = Math.ceil(total / pageSize);
  if (pageCount <= 1) return null;
  const first = page * pageSize + 1;
  const last = Math.min(total, (page + 1) * pageSize);

  return (
    <div className="flex items-center justify-between mt-4 text-sm text-dark-text-muted">
      <span>
        Showing {first.toLocaleString()}–{last.toLocaleString()} of {total.toLocaleString()} runs
      </span>
      <div className="flex items-center gap-3">
        <button
          onClick={() => onPageChange(page - 1)}
          disabled={page === 0}
          className="btn-secondary flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <ChevronLeft size={16} />
          Previous
        </button>
        <span>
          Page {page + 1} of {pageCount}
        </span>
        <button
          onClick={() => onPageChange(page + 1)}
          disabled={page >= pageCount - 1}
          className="btn-secondary flex items-center gap-1 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next
          <ChevronRight size={16} />
        </button>
      </div>
    </div>
  );
}
