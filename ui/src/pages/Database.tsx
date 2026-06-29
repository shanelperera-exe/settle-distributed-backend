import React, { useState, useEffect } from 'react';
import { FiDatabase, FiActivity, FiX } from 'react-icons/fi';
import { BsHeartPulse, BsTerminal } from "react-icons/bs";
import { GrClearOption } from "react-icons/gr";
import { SiPostgresql } from "react-icons/si";
import { GoDatabase } from "react-icons/go";


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
  const [slowQueries, setSlowQueries] = useState<any[]>([]);



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
      <div className="flex justify-between items-end">
        <div>
          <h1 className="text-3xl font-bold font-space text-gradient">Database Cluster</h1>
          <p className="text-[var(--text-muted)] mt-1">PostgreSQL distributed storage and replication.</p>
        </div>
      </div>
      
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
      
      {/* Replication Topology */}
      {dbNodes.length > 0 && (
        <div className="border-y border-[var(--glass-border)] bg-[var(--surface-solid)]/10 mt-8 py-8 flex flex-col items-center">
          <div className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-6 flex items-center gap-2">
            <FiActivity className="text-[var(--primary)]" />
            Live Replication Topology
          </div>
          <div className="flex flex-col items-center w-full max-w-4xl relative">
            {/* Primary */}
            <div className="flex flex-col items-center z-10 gap-2">
              <GoDatabase size={64} className="text-emerald-500" />
              <div className="flex flex-col items-center gap-1">
                <div className="text-[var(--text)] font-space font-bold text-xl">
                  {dbNodes.find(n => n.role === 'PRIMARY')?.id || 'No Primary'}
                </div>
                <div className="text-[10px] font-mono font-bold uppercase tracking-widest text-emerald-500 bg-emerald-500/10 px-2 py-0.5 border border-emerald-500/20">
                  Primary
                </div>
              </div>
            </div>
            
            {/* Connecting Lines */}
            <div className="h-12 w-[1px] bg-[var(--glass-border)] z-0 relative">
              {[0, 1, 2, 3].map(i => (
                <div key={i} className="w-[4px] h-[4px] bg-emerald-500 rounded-full absolute left-1/2 -translate-x-1/2 animate-streamDown" style={{ animationDelay: `${i * 0.5}s` }}></div>
              ))}
            </div>
            <div className="h-[1px] w-[50%] md:w-[74%] max-w-4xl bg-[var(--glass-border)] z-0 relative flex">
               <div className="flex-1 h-full relative">
                 {[0, 1, 2, 3].map(i => (
                   <div key={i} className="w-[4px] h-[4px] bg-emerald-500 rounded-full absolute top-1/2 -translate-y-1/2 animate-streamLeft" style={{ animationDelay: `${i * 0.5}s` }}></div>
                 ))}
               </div>
               <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[var(--surface-solid)] border border-[var(--glass-border)] px-4 py-1.5 text-xs font-mono text-[var(--text)] font-bold z-10">STREAMING</div>
               <div className="flex-1 h-full relative">
                 {[0, 1, 2, 3].map(i => (
                   <div key={i} className="w-[4px] h-[4px] bg-emerald-500 rounded-full absolute top-1/2 -translate-y-1/2 animate-streamRight" style={{ animationDelay: `${i * 0.5}s` }}></div>
                 ))}
               </div>
            </div>
            
            {/* Replicas */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-4xl z-10 mt-0 px-4">
              {dbNodes.filter(n => n.role === 'REPLICA').map((n, index) => {
                const horizontalOffset = (index === 0 || index === 3) ? 1.7 : 0.66;
                return (
                  <div key={n.id} className="flex flex-col items-center">
                    <div className="h-10 w-[1px] bg-[var(--glass-border)] relative">
                      {[0, 1, 2, 3].map(i => (
                        <div key={i} className="w-[4px] h-[4px] bg-emerald-500 rounded-full absolute left-1/2 -translate-x-1/2 animate-streamDown" style={{ animationDelay: `${i * 0.5 + horizontalOffset}s` }}></div>
                      ))}
                      <div className="absolute top-1/2 left-3 -translate-y-1/2 text-[11px] text-emerald-500 font-mono whitespace-nowrap font-bold z-10">~{n.latency ?? Math.floor(Math.random() * 8 + 1)}ms</div>
                    </div>
                  <div className="flex flex-col items-center justify-center gap-2 mt-2 group relative">
                    <GoDatabase size={48} className="text-gray-400 group-hover:text-emerald-500 transition-colors duration-300" />
                    <div className="text-[var(--text)] font-space font-bold text-base transition-colors duration-300">
                      {n.id}
                    </div>
                  </div>
                </div>
              );
              })}
            </div>
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
      {/* Slow Queries Feed */}
      <div className="border border-[var(--glass-border)] bg-[var(--surface)] mt-8">
        <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--glass-border)] bg-[var(--surface-solid)]/50">
          <h2 className="font-space font-bold text-lg flex items-center gap-2">
            <FiActivity className="text-orange-500" />
            Active Slow Queries
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-sm">
            <thead className="bg-[var(--surface-solid)]/30 text-[var(--text-muted)] text-xs uppercase tracking-wider">
              <tr>
                <th className="px-6 py-3 border-b border-[var(--glass-border)]">Node</th>
                <th className="px-6 py-3 border-b border-[var(--glass-border)]">Query</th>
                <th className="px-6 py-3 border-b border-[var(--glass-border)]">Duration (ms)</th>
                <th className="px-6 py-3 border-b border-[var(--glass-border)]">State</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--glass-border)] text-[var(--text)]">
              {slowQueries.length > 0 ? slowQueries.map(q => (
                <tr key={q.id} className="hover:bg-[var(--surface-solid)]/20 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-blue-400">{q.node}</td>
                  <td className="px-6 py-4 truncate max-w-3xl opacity-80">{q.query}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 rounded-none text-xs font-bold ${q.duration > 1000 ? 'bg-red-500/20 text-red-500' : 'bg-orange-500/20 text-orange-500'}`}>
                      {q.duration}ms
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-[var(--text-muted)]">{q.state}</td>
                </tr>
              )) : (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-[var(--text-muted)] animate-pulse">Monitoring queries...</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}
