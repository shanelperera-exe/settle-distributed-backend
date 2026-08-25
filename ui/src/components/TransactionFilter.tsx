import React, { useState } from 'react';
import { FiSearch, FiFilter, FiX } from 'react-icons/fi';
import { motion, AnimatePresence } from 'framer-motion';

export interface FilterValues {
  customer_id: string;
  amount: string;
  transaction_id: string;
  start_date: string;
  end_date: string;
}

interface TransactionFilterProps {
  onFilter: (filters: FilterValues) => void;
  isLoading: boolean;
}

export const TransactionFilter: React.FC<TransactionFilterProps> = ({ onFilter, isLoading }) => {
  const [expanded, setExpanded] = useState(false);
  const [filters, setFilters] = useState<FilterValues>({
    customer_id: '',
    amount: '',
    transaction_id: '',
    start_date: '',
    end_date: ''
  });
  
  // Also keep track of a quick search that maps to transaction_id or customer_id
  const [quickSearch, setQuickSearch] = useState('');

  const handleApply = () => {
    // If quickSearch is populated but specific filters aren't, try to guess
    const finalFilters = { ...filters };
    if (quickSearch) {
      if (quickSearch.startsWith('pi_') || quickSearch.startsWith('txn_')) {
        finalFilters.transaction_id = quickSearch;
      } else if (quickSearch.startsWith('cus_') || quickSearch.startsWith('acc_')) {
        finalFilters.customer_id = quickSearch;
      } else {
        // Default to transaction ID for arbitrary text
        finalFilters.transaction_id = quickSearch;
      }
    }
    onFilter(finalFilters);
  };

  const clearFilters = () => {
    setQuickSearch('');
    setFilters({
      customer_id: '',
      amount: '',
      transaction_id: '',
      start_date: '',
      end_date: ''
    });
    onFilter({
      customer_id: '',
      amount: '',
      transaction_id: '',
      start_date: '',
      end_date: ''
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleApply();
    }
  };

  return (
    <div className="w-full bg-[var(--surface)] border border-[var(--glass-border)] rounded-none mb-6 font-space">
      <div className="flex items-center p-2">
        <div className="flex-1 relative flex items-center">
          <FiSearch className="absolute left-4 text-[var(--text-muted)] text-lg" />
          <input
            type="text"
            placeholder="Search by Intent ID (pi_...) or Customer ID (cus_...)"
            value={quickSearch}
            onChange={(e) => setQuickSearch(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full bg-transparent border-none pl-12 pr-4 py-3 outline-none text-[var(--text)] placeholder-[var(--text-muted)]/50"
          />
        </div>
        
        <div className="h-8 w-px bg-[var(--glass-border)] mx-2"></div>
        
        <button
          onClick={() => setExpanded(!expanded)}
          className={`px-4 py-2 flex items-center gap-2 text-sm font-bold uppercase tracking-wider transition-colors border ${expanded ? 'bg-[var(--primary)] text-white border-[var(--primary)]' : 'bg-transparent text-[var(--text-muted)] border-transparent hover:text-[var(--text)] hover:bg-[var(--surface-solid)]'}`}
        >
          <FiFilter /> Filters
        </button>
        
        <button
          onClick={handleApply}
          disabled={isLoading}
          className="ml-2 px-6 py-2 bg-[var(--primary)] hover:bg-green-600 text-[var(--background)] font-bold text-sm uppercase tracking-wider transition-colors disabled:opacity-50"
        >
          {isLoading ? 'Searching...' : 'Search'}
        </button>
        
        {(quickSearch || Object.values(filters).some(v => v !== '')) && (
          <button
            onClick={clearFilters}
            className="ml-2 px-3 py-2 text-[var(--text-muted)] hover:text-red-500 transition-colors"
            title="Clear filters"
          >
            <FiX className="text-xl" />
          </button>
        )}
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden border-t border-[var(--glass-border)] bg-[var(--surface-solid)]/30"
          >
            <div className="p-6 grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="space-y-2">
                <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Exact Amount</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--text-muted)]">$</span>
                  <input
                    type="number"
                    step="0.01"
                    placeholder="e.g. 100.00"
                    value={filters.amount}
                    onChange={(e) => setFilters({...filters, amount: e.target.value})}
                    onKeyDown={handleKeyDown}
                    className="w-full bg-[var(--background)] border border-[var(--glass-border)] pl-8 pr-3 py-2 outline-none focus:border-[var(--primary)] text-sm text-[var(--text)]"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Start Date</label>
                <input
                  type="date"
                  value={filters.start_date}
                  onChange={(e) => setFilters({...filters, start_date: e.target.value})}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-[var(--background)] border border-[var(--glass-border)] px-3 py-2 outline-none focus:border-[var(--primary)] text-sm text-[var(--text)]"
                />
              </div>
              
              <div className="space-y-2">
                <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">End Date</label>
                <input
                  type="date"
                  value={filters.end_date}
                  onChange={(e) => setFilters({...filters, end_date: e.target.value})}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-[var(--background)] border border-[var(--glass-border)] px-3 py-2 outline-none focus:border-[var(--primary)] text-sm text-[var(--text)]"
                />
              </div>
              
              <div className="space-y-2">
                <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Customer ID</label>
                <input
                  type="text"
                  placeholder="e.g. cus_123"
                  value={filters.customer_id}
                  onChange={(e) => setFilters({...filters, customer_id: e.target.value})}
                  onKeyDown={handleKeyDown}
                  className="w-full bg-[var(--background)] border border-[var(--glass-border)] px-3 py-2 outline-none focus:border-[var(--primary)] text-sm text-[var(--text)]"
                />
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
