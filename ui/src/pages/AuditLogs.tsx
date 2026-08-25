import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { FiCpu, FiAlertTriangle, FiActivity } from 'react-icons/fi';
import { MdOutlineSecurity } from "react-icons/md";
import { LuLogs } from "react-icons/lu";

interface AuditLog {
  timestamp?: string;
  event: string;
  node_id?: string;
  message?: string;
  [key: string]: any;
}

export default function AuditLogs() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchLogs();
    const interval = setInterval(fetchLogs, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  const fetchLogs = async () => {
    try {
      const res = await fetch('/api/v1/audit/logs?limit=200', {
        headers: {
          'Authorization': `Bearer ${import.meta.env.VITE_API_KEY || 'settle-dev-key-12345'}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setLogs(data);
        setError(null);
      } else {
        setError('Failed to fetch audit logs');
      }
    } catch (err) {
      setError('Network error reaching audit service');
    } finally {
      setLoading(false);
    }
  };

  const getEventIcon = (event: string) => {
    if (event === 'CHAOS_INJECTION') return <FiAlertTriangle className="text-red-500" />;
    if (event === 'LEADER_ELECTION') return <MdOutlineSecurity className="text-amber-500" />;
    if (event === 'NODE_START') return <FiCpu className="text-green-500" />;
    return <FiActivity className="text-[var(--text-muted)]" />;
  };

  const getEventColor = (event: string) => {
    if (event === 'CHAOS_INJECTION') return 'text-red-500 border-red-500/30 bg-red-500/10';
    if (event === 'LEADER_ELECTION') return 'text-amber-500 border-amber-500/30 bg-amber-500/10';
    if (event === 'NODE_START') return 'text-green-500 border-green-500/30 bg-green-500/10';
    return 'text-[var(--text-muted)] border-[var(--glass-border)] bg-[var(--surface-solid)]';
  };

  return (
    <div className="space-y-8 pb-12 font-space">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col md:flex-row md:items-center justify-between gap-4"
      >
        <div className="flex items-center gap-3">
          <div className="text-[var(--primary)]">
            <LuLogs size={48} />
          </div>
          <div>
            <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">Audit Logs</h1>
            <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest flex items-center gap-2">
              Immutable System Ledger
            </p>
          </div>
        </div>
        
        <div className="flex items-center gap-4 border border-[var(--glass-border)] p-2 bg-[var(--surface)]">
          <div className="flex flex-col items-end border-r border-[var(--glass-border)] pr-4">
            <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Log Provider</span>
            <span className="text-sm font-bold text-[var(--text)]">Grafana Loki</span>
          </div>
          <div className="flex flex-col items-start pl-2">
            <span className="text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Status</span>
            <span className="text-sm font-bold text-green-500 flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span> Streaming
            </span>
          </div>
        </div>
      </motion.div>

      <div className="glass-card overflow-hidden">
        {error ? (
          <div className="p-8 text-center text-red-500 font-bold border-b border-[var(--glass-border)] bg-red-500/5">
            {error}
          </div>
        ) : null}
        
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse font-google-code text-sm">
            <thead>
              <tr className="border-b border-[var(--glass-border)] bg-[var(--surface-solid)]/50">
                <th className="py-4 px-6 font-bold text-[var(--text-muted)] uppercase tracking-widest text-xs w-48">Timestamp</th>
                <th className="py-4 px-6 font-bold text-[var(--text-muted)] uppercase tracking-widest text-xs w-48">Event Type</th>
                <th className="py-4 px-6 font-bold text-[var(--text-muted)] uppercase tracking-widest text-xs w-32">Node ID</th>
                <th className="py-4 px-6 font-bold text-[var(--text-muted)] uppercase tracking-widest text-xs">Message / Payload</th>
              </tr>
            </thead>
            <tbody>
              {loading && logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-[var(--text-muted)]">
                    <FiActivity className="animate-spin inline-block mr-2" /> Loading immutable ledger...
                  </td>
                </tr>
              ) : logs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="py-12 text-center text-[var(--text-muted)]">
                    No system events recorded yet.
                  </td>
                </tr>
              ) : (
                logs.map((log, idx) => (
                  <tr key={idx} className="border-b border-[var(--glass-border)] hover:bg-[var(--surface-solid)]/30 transition-colors">
                    <td className="py-4 px-6 whitespace-nowrap text-[var(--text-muted)]">
                      {log.timestamp ? new Date(log.timestamp).toLocaleString() : 'N/A'}
                    </td>
                    <td className="py-4 px-6">
                      <span className={`inline-flex items-center gap-2 px-2.5 py-1 text-xs font-bold uppercase tracking-wider border rounded-none ${getEventColor(log.event)}`}>
                        {getEventIcon(log.event)}
                        {log.event}
                      </span>
                    </td>
                    <td className="py-4 px-6 font-bold text-[var(--text)]">
                      {log.node_id || log.node || '*'}
                    </td>
                    <td className="py-4 px-6 text-[var(--text-muted)] break-all">
                      <span className="text-[var(--text)]">{log.message}</span>
                      {Object.keys(log).length > 4 && (
                        <div className="mt-2 text-xs opacity-70 p-2 bg-[var(--background)] border border-[var(--glass-border)]">
                          {JSON.stringify(Object.fromEntries(Object.entries(log).filter(([k]) => !['timestamp', 'event', 'node_id', 'message', 'node', 'service', 'job', 'stream', 'filename'].includes(k))))}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
