import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';
import { FiDatabase, FiActivity, FiX } from 'react-icons/fi';
import { BsHeartPulse, BsTerminal } from "react-icons/bs";
import { GrClearOption } from "react-icons/gr";
import { SiPostgresql } from "react-icons/si";

// Same LogEntry as Nodes.tsx for consistency
const LogEntry = ({ logString }: { logString: string }) => {
  const [expanded, setExpanded] = useState(false);
  try {
    const log = JSON.parse(logString);
    if (log && log.message) {
      const { timestamp, severity, message, ...rest } = log;
      const hasDetails = Object.keys(rest).length > 0;
      return (
        <div className="flex flex-col hover:bg-[var(--surface-solid)]/30 px-2 py-1.5 -mx-2 rounded-none transition-colors group cursor-pointer" onClick={() => hasDetails && setExpanded(!expanded)}>
          <div className="flex flex-col sm:flex-row gap-2 sm:gap-4 items-start">
            <span className="text-[var(--text-muted)] min-w-[120px] flex-shrink-0 pt-0.5">
              {timestamp ? new Date(timestamp).toLocaleTimeString(undefined, { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit', fractionalSecondDigits: 3 }) : ''}
            </span>
            {severity && (
              <span className={`font-bold flex-shrink-0 min-w-[75px] pt-0.5 ${
                severity === 'ERROR' ? 'text-red-500' :
                severity === 'WARN' ? 'text-yellow-500' :
                severity === 'DEBUG' ? 'text-gray-400' :
                'text-[var(--primary)]'
              }`}>
                {severity}
              </span>
            )}
            <span className="text-[var(--text)] font-medium flex-1 pt-0.5">{message}</span>
            {hasDetails && (
              <span className="text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity text-xs px-2 pt-0.5">
                {expanded ? 'Collapse' : 'Expand'}
              </span>
            )}
          </div>
          {expanded && hasDetails && (
            <div className="mt-3 mb-1 sm:ml-[152px] p-4 bg-[var(--surface-solid)]/40 backdrop-blur-sm rounded-none border border-[var(--glass-border)] text-[12px] font-mono shadow-inner overflow-x-auto">
              <div className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1.5">
                {Object.entries(rest).map(([key, val]) => (
                  <React.Fragment key={key}>
                    <span className="text-[var(--text-muted)] text-right opacity-80">{key}:</span>
                    <span className="text-[var(--text)] break-all">{typeof val === 'object' ? JSON.stringify(val) : String(val)}</span>
                  </React.Fragment>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }
  } catch (e) {
    // Fallback for non-JSON lines
  }
  return <div className="mb-1 leading-relaxed px-2 hover:bg-[var(--surface-solid)]/30 -mx-2 rounded-none py-1">{logString}</div>;
};
const PROMETHEUS_URL = 'http://localhost:9090';

async function fetchPrometheusQuery(query: string) {
  try {
    const res = await fetch(`${PROMETHEUS_URL}/api/v1/query?query=${encodeURIComponent(query)}`);
    const json = await res.json();
    return json.data?.result || [];
  } catch (e) {
    console.error("Prometheus fetch error:", e);
    return [];
  }
}

export default function Database() {
  const [dbNodes, setDbNodes] = useState<any[]>([]);
  const [activeTerminalNode, setActiveTerminalNode] = useState<string | null>(null);
  const [nodeLogs, setNodeLogs] = useState<string[]>([]);
  const [clearedLogLines, setClearedLogLines] = useState<Set<string>>(new Set());



  useEffect(() => {
    const fetchSlowQueries = async () => {
      try {
        const res = await fetch('/api/v1/database/slow_queries');
        const queries = await res.json();
        if (Array.isArray(queries)) {
          setSlowQueries(queries);
        }
      } catch(e) {
        console.error("Slow queries fetch error:", e);
      }
    };
    
    fetchSlowQueries();
    const qInterval = setInterval(fetchSlowQueries, 4000);
    return () => clearInterval(qInterval);
  }, []);

  useEffect(() => {
    // Generate initial static nodes
    const initialNodes = Array.from({ length: 5 }, (_, i) => ({
      id: `postgres-${i + 1}`,
      role: 'REPLICA',
      status: 'HEALTHY',
      connections: 0,
      cpu: 0,
      memory: 0,
      storage: 0,
      tps: 0,
      tpsHistory: Array.from({ length: 15 }, () => 0),
      latency: 0,
    }));
    setDbNodes(initialNodes);

    const fetchMetrics = async () => {
      try {
        const res = await fetch('/api/v1/database/metrics');
        const metrics = await res.json();
        if (Array.isArray(metrics)) {
          setDbNodes((prev) => 
            metrics.map(metric => {
              const prevNode = prev.find(n => n.id === metric.id) || initialNodes.find(n => n.id === metric.id) || metric;
              return {
                ...metric,
                tpsHistory: [...(prevNode.tpsHistory || Array.from({ length: 15 }, () => 0)).slice(1), metric.tps],
              };
            })
          );
        }
      } catch (e) {
        console.error("Database metrics fetch error:", e);
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 2000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let logInterval: any;
    if (activeTerminalNode) {
      // If we had a postgres-exporter or Loki logs for postgres, we would fetch them here.
      // For now, since it's a simulated UI, we simulate some database logs.
      const addMockLog = () => {
        const severities = ['INFO', 'INFO', 'INFO', 'DEBUG', 'WARN'];
        const actions = ['CHECKPOINT starting', 'LOG: connection received', 'LOG: statement: SELECT 1', 'LOG: replication sync', 'LOG: unexpected EOF on client connection'];
        const severity = severities[Math.floor(Math.random() * severities.length)];
        const message = actions[Math.floor(Math.random() * actions.length)];
        
        const logObj = {
          timestamp: new Date().toISOString(),
          severity,
          message,
          node_id: activeTerminalNode,
          component: 'postgres',
        };
        
        setNodeLogs(prev => {
          const newLogs = [...prev, JSON.stringify(logObj)];
          if (newLogs.length > 100) return newLogs.slice(newLogs.length - 100);
          return newLogs;
        });
      };
      
      // Add a log every 1.5 seconds
      logInterval = setInterval(addMockLog, 1500);
    } else {
      setNodeLogs([]);
      setClearedLogLines(new Set());
    }
    return () => clearInterval(logInterval);
  }, [activeTerminalNode]);

  return (
    <div className="space-y-8 pb-12">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3"
      >
        <div className="text-[var(--primary)]">
          <FiDatabase size={48} />
        </div>
        <div>
          <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">Database Cluster</h1>
          <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest">PostgreSQL distributed storage and replication.</p>
        </div>
      </motion.div>
      
      {dbNodes.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 border-y border-[var(--glass-border)] mt-8">
          <div className="p-6 border-r border-[var(--glass-border)] bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2"><FiDatabase className="text-[var(--text-muted)]" /> Total Instances</p>
            <p className="text-3xl font-bold text-[var(--text)]">{dbNodes.length}</p>
          </div>
          <div className="p-6 border-r border-[var(--glass-border)] bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2 text-[var(--primary)]"><BsHeartPulse /> Active Primary</p>
            <p className="text-3xl font-bold text-[var(--primary)]">{dbNodes.find(n => n.role === 'PRIMARY')?.id || 'None'}</p>
          </div>
          <div className="p-6 border-r border-[var(--glass-border)] bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2 text-emerald-500"><FiActivity /> Active Connections</p>
            <p className="text-3xl font-bold text-[var(--text)]">{Math.floor(dbNodes.reduce((sum, n) => sum + (n.connections || 0), 0))}</p>
          </div>
          <div className="p-6 bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2 text-purple-500"><FiActivity /> Total Cluster TPS</p>
            <p className="text-3xl font-bold text-[var(--text)]">{Math.floor(dbNodes.reduce((sum, n) => sum + (n.tps || 0), 0))}</p>
          </div>
        </div>
      )}
      


      {dbNodes.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-5 border-y border-[var(--glass-border)] mt-8">
          {dbNodes.map((node, index) => {
            return (
              <div key={node.id} className={`py-12 px-8 flex flex-col items-center justify-center text-center relative ${index !== 0 ? 'lg:border-l border-[var(--glass-border)]' : ''}`}>
                <div className="absolute top-4 right-4 cursor-pointer text-[var(--text-muted)] hover:text-[var(--text)] transition-colors" onClick={() => setActiveTerminalNode(activeTerminalNode === node.id ? null : node.id)}>
                  <BsTerminal size={20} className={activeTerminalNode === node.id ? 'text-[var(--primary)]' : ''} />
                </div>
                <SiPostgresql className={`text-4xl mb-4 opacity-80 ${node.role === 'PRIMARY' ? 'text-emerald-500' : 'text-gray-400'}`} />
                <p className={`text-4xl font-light mb-3 ${node.role === 'PRIMARY' ? 'text-emerald-500' : 'text-[var(--text)]'}`}>{node.id}</p>
                <div className="mb-6 h-[40px] flex items-center justify-center">
                  <span className={`text-xs font-bold px-4 py-1.5 rounded-none font-space uppercase tracking-wider text-white ${node.role === 'PRIMARY' ? 'bg-emerald-500' : 'bg-gray-500'}`}>
                    {node.role}
                  </span>
                </div>
                
                <div className="w-full space-y-3 mt-2 pt-6 border-t border-[var(--glass-border)]/50">
                  <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                    <span className="flex items-center gap-1.5"><BsHeartPulse /> Status</span>
                    <span className={`font-bold flex items-center gap-1.5 ${node.status === 'HEALTHY' ? 'text-emerald-500' : 'text-red-500'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${node.status === 'HEALTHY' ? 'bg-emerald-500' : 'bg-red-500'}`}></span> {node.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                    <span className="flex items-center gap-1.5"><FiActivity /> Connections</span>
                    <span className="text-[var(--text)]">{Math.floor(node.connections)}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                    <span className="flex items-center gap-1.5"><FiDatabase /> Storage</span>
                    <span className="text-[var(--text)]">{node.storage ? node.storage.toFixed(1) : '0'} GB</span>
                  </div>
                  <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                    <span className="flex items-center gap-1.5"><FiActivity /> TPS</span>
                    <span className="text-[var(--text)]">{node.tps ? node.tps.toFixed(1) : '0'}</span>
                  </div>
                  <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                    <span className="flex items-center gap-1.5"><FiActivity /> Replication Lag</span>
                    {node.role === 'REPLICA' ? (
                      <span className={`font-bold ${(node.latency ?? 0) > 5 ? 'text-orange-500' : 'text-[var(--text)]'}`}>
                        {node.latency ?? Math.floor(Math.random() * 8 + 1)}ms
                      </span>
                    ) : (
                      <span className="text-[var(--text-muted)] opacity-50">N/A</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="py-24 text-center text-[var(--text-muted)]">
          <p>Loading database members...</p>
        </div>
      )}


      {/* Terminal Section */}
      {activeTerminalNode && (
        <div className="border border-[var(--glass-border)] bg-[var(--surface)] mt-8 flex flex-col h-[600px]">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--glass-border)] bg-[var(--surface-solid)]">
            <div className="flex items-center gap-2">
              <BsTerminal className="text-[var(--primary)]" />
              <span className="font-space font-bold text-sm text-[var(--text)]">{activeTerminalNode} LOGS</span>
            </div>
            <div className="flex items-center gap-4">
              <button onClick={() => setClearedLogLines(new Set(nodeLogs))} className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors" title="Clear Terminal">
                <GrClearOption size={17} />
              </button>
              <button onClick={() => setActiveTerminalNode(null)} className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors" title="Close Terminal">
                <FiX size={20} />
              </button>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto p-6 font-mono text-[13px] text-[var(--text)] opacity-95 break-all whitespace-pre-wrap flex flex-col gap-1">
            {nodeLogs.filter(log => !clearedLogLines.has(log)).length > 0 ? (
              nodeLogs.filter(log => !clearedLogLines.has(log)).map((logString, i) => <LogEntry key={i} logString={logString} />)
            ) : (
              <div className="animate-pulse text-[var(--text-muted)] flex items-center justify-center h-full">Waiting for logs...</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
