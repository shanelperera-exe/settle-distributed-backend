import React, { useState, useEffect } from 'react';
import { FiServer, FiCpu, FiHardDrive, FiActivity, FiX, FiAlertTriangle } from 'react-icons/fi';
import { FaCircleNodes } from "react-icons/fa6";
import { BsHeartPulse, BsTerminal } from "react-icons/bs";
import { GrClearOption } from "react-icons/gr";
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { motion } from 'framer-motion';


type MetricHistory = { time: number; val: number };

type NodeData = {
  id: string;
  role: string;
  status: string;
  cpu: number;
  cpuHistory: MetricHistory[];
  memory: number;
  memHistory: MetricHistory[];
  tps: number;
  tpsHistory: MetricHistory[];
  raftTerm: number;
  raftCommitIndex: number;
  raftLag: number;
  netRx: number;
  netTx: number;
  logWarnings: number;
};

const LogEntry = ({ logString }: { logString: string }) => {
  const [expanded, setExpanded] = useState(false);
  try {
    const log = JSON.parse(logString);
    if (log && log.message) {
      const { timestamp, severity, message, ...rest } = log;
      const hasDetails = Object.keys(rest).length > 0;
      return (
        <div className="flex flex-col hover:bg-[var(--surface-solid)]/30 px-2 py-1.5 -mx-2 rounded transition-colors group cursor-pointer" onClick={() => hasDetails && setExpanded(!expanded)}>
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
            <div className="mt-3 mb-1 sm:ml-[152px] p-4 bg-[var(--surface-solid)]/40 backdrop-blur-sm rounded-md border border-[var(--glass-border)] text-[12px] font-mono shadow-inner overflow-x-auto">
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
  return <div className="mb-1 leading-relaxed px-2 hover:bg-[var(--surface-solid)]/30 -mx-2 rounded py-1">{logString}</div>;
};

const Sparkline = ({ data, dataKey, color }: { data: any[], dataKey: string, color: string }) => (
  <div className="h-[25px] w-full mt-0.5">
    <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
      <AreaChart data={data}>
        <defs>
          <linearGradient id={`grad-${dataKey}-${color.replace('#','')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor={color} stopOpacity={0.4}/>
            <stop offset="95%" stopColor={color} stopOpacity={0}/>
          </linearGradient>
        </defs>
        <Area type="monotone" dataKey={dataKey} stroke={color} fill={`url(#grad-${dataKey}-${color.replace('#','')})`} strokeWidth={1.5} isAnimationActive={false} />
      </AreaChart>
    </ResponsiveContainer>
  </div>
);

export default function Nodes() {
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [activeTerminalNode, setActiveTerminalNode] = useState<string | null>(null);
  const [nodeLogs, setNodeLogs] = useState<string[]>([]);
  const [clearedLogLines, setClearedLogLines] = useState<Set<string>>(new Set());

  useEffect(() => {
    let interval: any;

    const fetchTopologyData = async () => {
      try {
        let clusterMembers = ['node-1', 'node-2', 'node-3', 'node-4', 'node-5'];
        try {
          const healthRes = await fetch('/api/v1/health/cluster');
          if (healthRes.ok) {
            const healthData = await healthRes.json();
            if (healthData.cluster_members && healthData.cluster_members.length > 0) {
              clusterMembers = healthData.cluster_members;
            }
          }
        } catch (e) {
          console.warn('Failed to fetch cluster health', e);
        }

        const [roleRes, cpuRes, memRes, tpsRes, raftTermRes, raftIndexRes, raftLagRes, netRxRes, netTxRes] = await Promise.all([
          fetch('/prometheus/api/v1/query?query=raft_node_role').catch(() => null),
          fetch('/prometheus/api/v1/query?query=sum(rate(process_cpu_seconds_total{instance=~".*settle-node.*"}[1m])) by (instance)').catch(() => null),
          fetch('/prometheus/api/v1/query?query=sum(process_resident_memory_bytes{instance=~".*settle-node.*"}) by (instance)').catch(() => null),
          fetch('/prometheus/api/v1/query?query=sum(rate(http_requests_total[1m])) by (instance)').catch(() => null),
          fetch('/prometheus/api/v1/query?query=raft_current_term').catch(() => null),
          fetch('/prometheus/api/v1/query?query=raft_commit_index').catch(() => null),
          fetch('/prometheus/api/v1/query?query=raft_replication_lag').catch(() => null),
          fetch('/prometheus/api/v1/query?query=sum(rate(process_network_receive_bytes_total{instance=~".*settle-node.*"}[1m])) by (instance)').catch(() => null),
          fetch('/prometheus/api/v1/query?query=sum(rate(process_network_transmit_bytes_total{instance=~".*settle-node.*"}[1m])) by (instance)').catch(() => null),
        ]);

        const parsePrometheus = async (res: any, callback: (id: string, val: number, metric: any) => void) => {
          if (res && res.ok) {
            const data = await res.json();
            data?.data?.result?.forEach((r: any) => {
              let id = r.metric.node_id;
              if (!id && r.metric.instance) {
                id = r.metric.instance.split(':')[0].replace('settle-', '');
              }
              if (id) {
                callback(id, parseFloat(r.value[1]), r.metric);
              }
            });
          }
        };

        const updates: Record<string, Partial<NodeData>> = {};
        clusterMembers.forEach(id => updates[id] = { id });

        await parsePrometheus(roleRes, (id, val, metric) => { if (val === 1 && updates[id]) updates[id].role = metric.role; });
        await parsePrometheus(cpuRes, (id, val) => { if (updates[id]) updates[id].cpu = parseFloat((val * 100).toFixed(2)); });
        await parsePrometheus(memRes, (id, val) => { if (updates[id]) updates[id].memory = parseFloat((val / (1024 * 1024)).toFixed(2)); });
        await parsePrometheus(tpsRes, (id, val) => { if (updates[id]) updates[id].tps = val; });
        await parsePrometheus(raftTermRes, (id, val) => { if (updates[id]) updates[id].raftTerm = val; });
        await parsePrometheus(raftIndexRes, (id, val) => { if (updates[id]) updates[id].raftCommitIndex = val; });
        await parsePrometheus(raftLagRes, (id, val) => { if (updates[id]) updates[id].raftLag = val; });
        await parsePrometheus(netRxRes, (id, val) => { if (updates[id]) updates[id].netRx = val; });
        await parsePrometheus(netTxRes, (id, val) => { if (updates[id]) updates[id].netTx = val; });

        setNodes(prev => {
          const now = Date.now();
          const maxHistory = 20;
          const nodeMap = new Map(prev.map(n => [n.id, n]));
          
          clusterMembers.forEach(id => {
            if (!nodeMap.has(id)) {
              nodeMap.set(id, { 
                id, role: 'FOLLOWER', status: 'Healthy', 
                cpu: 0, cpuHistory: [], memory: 0, memHistory: [], tps: 0, tpsHistory: [],
                raftTerm: 0, raftCommitIndex: 0, raftLag: 0, netRx: 0, netTx: 0, logWarnings: 0
              });
            }
          });

          Array.from(nodeMap.values()).forEach(node => {
            const update = updates[node.id] || {};
            node.role = update.role || node.role;
            node.cpu = update.cpu || 0;
            node.memory = update.memory || 0;
            node.tps = update.tps || 0;
            node.raftTerm = update.raftTerm || 0;
            node.raftCommitIndex = update.raftCommitIndex || 0;
            node.raftLag = update.raftLag || 0;
            node.netRx = update.netRx || 0;
            node.netTx = update.netTx || 0;
            
            node.cpuHistory = [...node.cpuHistory, { time: now, val: node.cpu }].slice(-maxHistory);
            node.memHistory = [...node.memHistory, { time: now, val: node.memory }].slice(-maxHistory);
            node.tpsHistory = [...node.tpsHistory, { time: now, val: node.tps }].slice(-maxHistory);
          });

          return Array.from(nodeMap.values()).sort((a, b) => a.id.localeCompare(b.id));
        });
        
      } catch (e) {
        console.error("Failed to fetch topology data", e);
      }
    };

    fetchTopologyData();
    interval = setInterval(fetchTopologyData, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    let checkInterval: any;
    if (nodes.length > 0) {
      const fetchWarnings = async () => {
        nodes.forEach(async (node) => {
          try {
            const res = await fetch(`/api/dev/logs/settle-${node.id}`);
            if (res.ok) {
              const data = await res.json();
              if (data.logs) {
                let warns = 0;
                data.logs.slice(-20).forEach((l: string) => {
                  if (l.includes('"severity":"WARN"') || l.includes('"severity":"ERROR"')) warns++;
                });
                setNodes(prev => prev.map(n => n.id === node.id ? { ...n, logWarnings: warns } : n));
              }
            }
          } catch (e) {}
        });
      };
      checkInterval = setInterval(fetchWarnings, 5000);
    }
    return () => clearInterval(checkInterval);
  }, [nodes.length > 0]);

  useEffect(() => {
    let logInterval: any;
    if (activeTerminalNode) {
      const fetchLogs = async () => {
        try {
          const res = await fetch(`/api/dev/logs/settle-${activeTerminalNode}`);
          if (res.ok) {
            const data = await res.json();
            if (data.logs) {
              setNodeLogs(data.logs);
            }
          }
        } catch (e) {
          console.error('Failed to fetch logs', e);
        }
      };
      
      fetchLogs();
      logInterval = setInterval(fetchLogs, 3000);
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
          <FaCircleNodes size={48} />
        </div>
        <div>
          <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">Cluster Nodes</h1>
          <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest">Real-time telemetry and cluster health monitoring.</p>
        </div>
      </motion.div>
      
      {nodes.length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-4 border-y border-[var(--glass-border)] mt-8">
          <div className="p-6 border-r border-[var(--glass-border)] bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2"><FiServer className="text-[var(--text-muted)]" /> Total Nodes</p>
            <p className="text-3xl font-bold text-[var(--text)]">{nodes.length}</p>
          </div>
          <div className="p-6 border-r border-[var(--glass-border)] bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2 text-[var(--primary)]"><BsHeartPulse /> Active Leader</p>
            <p className="text-3xl font-bold text-[var(--primary)]">{nodes.find(n => n.role === 'LEADER')?.id || 'None'}</p>
          </div>
          <div className="p-6 border-r border-[var(--glass-border)] bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2 text-emerald-500"><FiActivity /> Cluster TPS</p>
            <p className="text-3xl font-bold text-[var(--text)]">{nodes.reduce((sum, n) => sum + (n.tps || 0), 0).toFixed(2)}</p>
          </div>
          <div className="p-6 bg-[var(--surface)] hover:bg-[var(--surface-solid)] transition-all duration-300">
            <p className="text-[11px] text-[var(--text-muted)] font-space uppercase tracking-wider mb-2 flex items-center gap-2 text-blue-500"><FiCpu /> Avg CPU</p>
            <p className="text-3xl font-bold text-[var(--text)]">{(nodes.reduce((sum, n) => sum + (n.cpu || 0), 0) / nodes.length).toFixed(1)}%</p>
          </div>
        </div>
      )}


      {nodes.length > 0 ? (
        <div className="grid grid-cols-1 lg:grid-cols-5 border-y border-[var(--glass-border)]">
          {nodes.map((node, index) => {
            const isLeader = node.role === 'LEADER';
            return (
              <div key={node.id} className={`py-12 px-8 flex flex-col items-center justify-center text-center relative ${index !== 0 ? 'lg:border-l border-[var(--glass-border)]' : ''}`}>
                <div className="absolute top-4 right-4 flex items-center gap-3">
                  {node.logWarnings > 0 && (
                    <div className="relative group flex items-center justify-center cursor-help" title={`${node.logWarnings} recent warnings/errors`}>
                      <span className="absolute w-full h-full rounded-full bg-yellow-500/50 animate-ping"></span>
                      <FiAlertTriangle className="text-yellow-500 relative z-10" />
                    </div>
                  )}
                  <div className="cursor-pointer text-[var(--text-muted)] hover:text-[var(--text)] transition-colors" onClick={() => setActiveTerminalNode(activeTerminalNode === node.id ? null : node.id)}>
                    <BsTerminal size={20} className={activeTerminalNode === node.id ? 'text-[var(--primary)]' : ''} />
                  </div>
                </div>

                <FiServer className={`text-3xl mb-4 opacity-80 ${isLeader ? 'text-[var(--primary)]' : 'text-blue-500'}`} />
                <p className={`text-4xl font-light mb-3 ${isLeader ? 'text-[var(--primary)]' : 'text-blue-500'}`}>{node.id}</p>
                <div className="mb-6 h-[40px] flex items-center justify-center">
                  <span className={`text-xs font-bold px-4 py-1.5 rounded-none font-space uppercase tracking-wider text-white ${isLeader ? 'bg-emerald-500' : 'bg-gray-500'}`}>
                    {node.role}
                  </span>
                </div>
                
                <div className="w-full space-y-3 mt-2 pt-6 border-t border-[var(--glass-border)]/50">
                  <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                    <span className="flex items-center gap-1.5"><BsHeartPulse /> Status</span>
                    <span className="text-emerald-500 font-bold flex items-center gap-1.5">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span> {node.status}
                    </span>
                  </div>
                  
                  <div className="flex flex-col">
                    <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                      <span className="flex items-center gap-1.5"><FiCpu /> CPU</span>
                      <span className={(node.cpu || 0) > 80 ? 'text-red-500 font-bold' : 'text-[var(--text)]'}>{(node.cpu || 0).toFixed(1)}%</span>
                    </div>
                    <Sparkline data={node.cpuHistory} dataKey="val" color="#3b82f6" />
                  </div>

                  <div className="flex flex-col">
                    <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                      <span className="flex items-center gap-1.5"><FiHardDrive /> Memory</span>
                      <span className="text-[var(--text)]">{(node.memory || 0).toFixed(1)} MB</span>
                    </div>
                    <Sparkline data={node.memHistory} dataKey="val" color="#8b5cf6" />
                  </div>

                  <div className="flex flex-col">
                    <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                      <span className="flex items-center gap-1.5"><FiActivity /> TPS</span>
                      <span className="text-[var(--text)]">{(node.tps || 0).toFixed(2)}</span>
                    </div>
                    <Sparkline data={node.tpsHistory} dataKey="val" color="#10b981" />
                  </div>
                  
                  <div className="pt-3 mt-3 border-t border-[var(--glass-border)]/50 space-y-3">
                    <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                      <span className="flex items-center gap-1.5">Raft Term</span>
                      <span className="text-[var(--text)]">{node.raftTerm || '-'}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                      <span className="flex items-center gap-1.5">Commit Idx</span>
                      <span className="text-[var(--text)]">{node.raftCommitIndex || '-'}</span>
                    </div>
                    <div className="flex justify-between items-center text-sm font-space text-[var(--text-muted)]">
                      <span className="flex items-center gap-1.5">Net Rx/Tx</span>
                      <span className="text-[var(--text)]">{(node.netRx / 1024).toFixed(0)}/{(node.netTx / 1024).toFixed(0)} KB/s</span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="py-24 text-center text-[var(--text-muted)]">
          <p>Loading cluster members...</p>
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
