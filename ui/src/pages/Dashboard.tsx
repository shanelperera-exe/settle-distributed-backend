import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  LineChart, Line, 
  BarChart, Bar,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import { FiActivity, FiServer, FiCheckCircle, FiClock, FiAlertCircle, FiTrendingUp, FiXCircle } from 'react-icons/fi';
import { LuLayoutDashboard } from 'react-icons/lu';
import { Link } from 'react-router-dom';

// Types
interface TimeSeriesData {
  time: string;
  tps: number;
  latency: number;
  queueSize: number;
}

interface NodeData {
  name: string;
  cpu: number;
  memory: number;
}

interface Payment {
  payment_id: string;
  transaction_id: string;
  amount: number;
  currency: string;
  status: string;
  sender_id: string;
  receiver_id?: string;
  payment_method?: string;
  created_at?: string;
}

const COLORS = ['#8b5cf6', '#ef4444', '#f59e0b']; // Processed, Failed, Pending

export default function Dashboard() {
  const [timeSeries, setTimeSeries] = useState<TimeSeriesData[]>([]);
  const [nodeData, setNodeData] = useState<NodeData[]>([]);
  const [activeNodes, setActiveNodes] = useState(0);
  const [liveTps, setLiveTps] = useState(0);
  const [avgLatency, setAvgLatency] = useState(0);
  const [totalProcessed, setTotalProcessed] = useState(0);
  const [recentPayments, setRecentPayments] = useState<Payment[]>([]);
  const [paymentStats, setPaymentStats] = useState({ processed: 0, failed: 0, pending: 0 });
  const [raftInsights, setRaftInsights] = useState({ leaderChanges: 0, currentTerm: 0 });
  const [queueSize, setQueueSize] = useState(0);

  useEffect(() => {
    // Initial fetch
    fetchClusterStatus();
    fetchRecentPayments();
    fetchPrometheusMetrics();
    fetchNodeMetrics();

    const interval = setInterval(() => {
      fetchClusterStatus();
      fetchRecentPayments();
      fetchPrometheusMetrics();
      fetchNodeMetrics();
    }, 5000);

    return () => clearInterval(interval);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchClusterStatus() {
    try {
      const res = await fetch('/api/v1/health/cluster');
      if (res.ok) {
        const data = await res.json();
        setActiveNodes(data.healthy_node_count || 0);
      }
    } catch (e) {
      console.error('Failed to fetch cluster status', e);
    }
  };

  async function fetchRecentPayments() {
    try {
      const res = await fetch('/api/v1/payments/?limit=5', {
        headers: {
          'Authorization': `Bearer ${import.meta.env.VITE_API_KEY || 'settle-dev-key-12345'}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        const dataWithDates = data.map((p: any, idx: number) => ({
          ...p,
          created_at: p.created_at || new Date(Date.now() - idx * 1000 * 60 * 15).toISOString()
        }));
        setRecentPayments(dataWithDates);
      }
    } catch (e) {
      console.error('Failed to fetch payments', e);
    }
  };

  async function fetchNodeMetrics() {
    try {
      const cpuRes = await fetch('/prometheus/api/v1/query?query=sum(rate(process_cpu_seconds_total{instance=~".*settle-node.*"}[1m])) by (instance)');
      const memRes = await fetch('/prometheus/api/v1/query?query=sum(process_resident_memory_bytes{instance=~".*settle-node.*"}) by (instance)');
      
      if (cpuRes.ok && memRes.ok) {
        const cpuData = await cpuRes.json();
        const memData = await memRes.json();
        
        const nodes: Record<string, NodeData> = {};
        
        cpuData?.data?.result?.forEach((res: any) => {
          const instanceName = res.metric.instance ? res.metric.instance.split(':')[0] : 'unknown';
          const name = instanceName.replace('settle-', '');
          const cpu = parseFloat(res.value[1]) * 100; // convert to %
          nodes[name] = { name, cpu: parseFloat(cpu.toFixed(2)), memory: 0 };
        });

        memData?.data?.result?.forEach((res: any) => {
          const instanceName = res.metric.instance ? res.metric.instance.split(':')[0] : 'unknown';
          const name = instanceName.replace('settle-', '');
          const memoryBytes = parseFloat(res.value[1]);
          const memoryMB = memoryBytes / (1024 * 1024);
          if (nodes[name]) {
            nodes[name].memory = parseFloat(memoryMB.toFixed(2));
          } else {
            nodes[name] = { name, cpu: 0, memory: parseFloat(memoryMB.toFixed(2)) };
          }
        });
        
        const newNodes = Object.values(nodes).sort((a, b) => a.name.localeCompare(b.name));
        if (newNodes.length > 0) {
          setNodeData(newNodes);
        }
      }
    } catch (e) {
      console.error('Failed to fetch node metrics', e);
    }
  }

  async function fetchPrometheusMetrics() {
    try {
      // Fetch TPS
      const tpsRes = await fetch('/prometheus/api/v1/query?query=sum(rate(http_requests_total[1m]))');
      let newTps = 0;
      if (tpsRes.ok) {
        const tpsData = await tpsRes.json();
        const tpsVal = tpsData?.data?.result?.[0]?.value?.[1];
        newTps = tpsVal ? parseFloat(tpsVal) : 0;
        setLiveTps(Number(newTps.toFixed(2)));
      }

      // Fetch Latency
      const latRes = await fetch('/prometheus/api/v1/query?query=histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[1m])) by (le))');
      let currentLatency = avgLatency;
      if (latRes.ok) {
        const latData = await latRes.json();
        const latVal = latData?.data?.result?.[0]?.value?.[1];
        // Convert seconds to ms
        const newLat = latVal && !isNaN(latVal) ? (parseFloat(latVal) * 1000).toFixed(2) : 0;
        currentLatency = Number(newLat);
        setAvgLatency(currentLatency);
      }

      // Fetch Queue Size
      let newQueue = 0;
      const queueRes = await fetch('/prometheus/api/v1/query?query=sum(replication_queue_size)');
      if (queueRes.ok) {
        const queueData = await queueRes.json();
        const queueVal = queueData?.data?.result?.[0]?.value?.[1];
        if (queueVal) newQueue = parseInt(queueVal, 10);
        setQueueSize(newQueue);
      }

      // Update timeseries
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
      
      setTimeSeries(prev => {
        const newData = [...prev, {
          time: timeStr,
          tps: Number(newTps.toFixed(2)),
          latency: currentLatency,
          queueSize: newQueue
        }];
        if (newData.length > 20) return newData.slice(newData.length - 20);
        return newData;
      });

      // Fetch Payment Stats
      const statsRes = await Promise.all([
        fetch('/prometheus/api/v1/query?query=sum(payments_processed_total)'),
        fetch('/prometheus/api/v1/query?query=sum(payments_failed_total)'),
        fetch('/prometheus/api/v1/query?query=sum(payments_pending)')
      ]);
      const [procData, failData, pendData] = await Promise.all(statsRes.map(res => res.ok ? res.json() : null));
      const processed = parseInt(procData?.data?.result?.[0]?.value?.[1] || "0", 10);
      const failed = parseInt(failData?.data?.result?.[0]?.value?.[1] || "0", 10);
      const pending = parseInt(pendData?.data?.result?.[0]?.value?.[1] || "0", 10);
      setPaymentStats({ processed, failed, pending });
      setTotalProcessed(processed);

      // Fetch Raft Insights
      const raftRes = await Promise.all([
        fetch('/prometheus/api/v1/query?query=sum(raft_leader_changes_total)'),
        fetch('/prometheus/api/v1/query?query=max(raft_current_term)')
      ]);
      const [leaderData, termData] = await Promise.all(raftRes.map(res => res.ok ? res.json() : null));
      setRaftInsights({
        leaderChanges: parseInt(leaderData?.data?.result?.[0]?.value?.[1] || "0", 10),
        currentTerm: parseInt(termData?.data?.result?.[0]?.value?.[1] || "0", 10)
      });

    } catch (e) {
      console.error('Failed to fetch prometheus metrics', e);
    }
  };

  const pieData = [
    { name: 'Processed', value: paymentStats.processed },
    { name: 'Failed', value: paymentStats.failed },
    { name: 'Pending', value: paymentStats.pending }
  ];

  return (
    <div className="space-y-8 pb-12">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3"
      >
        <div className="text-[var(--primary)]">
          <LuLayoutDashboard size={48} />
        </div>
        <div>
          <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">Cluster Dashboard</h1>
          <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest">Real-time telemetry and cluster health monitoring</p>
        </div>
      </motion.div>

      {/* Top Stat Cards - Payments Style */}
      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="grid grid-cols-1 lg:grid-cols-4 border-y border-[var(--glass-border)]">
        <div className="py-12 px-8 flex flex-col items-center justify-center text-center relative">
          <FiActivity className="text-3xl text-[var(--primary)] mb-4 opacity-80" />
          <p className="text-5xl font-light text-[var(--primary)] mb-3">{liveTps}</p>
          <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">live cluster tps</span><br/>across the network</h3>
        </div>
        
        <div className="py-12 px-8 flex flex-col items-center justify-center text-center lg:border-l border-[var(--glass-border)]">
          <FiClock className="text-3xl text-amber-500 mb-4 opacity-80" />
          <p className="text-5xl font-light text-amber-500 mb-3">{avgLatency} <span className="text-xl">ms</span></p>
          <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">p95 global latency</span><br/>end-to-end processing</h3>
        </div>

        <div className="py-12 px-8 flex flex-col items-center justify-center text-center lg:border-l border-[var(--glass-border)]">
          <FiServer className={`text-3xl mb-4 opacity-80 ${activeNodes < 5 ? 'text-red-500' : 'text-blue-500'}`} />
          <p className={`text-5xl font-light mb-3 ${activeNodes < 5 ? 'text-red-500' : 'text-blue-500'}`}>{activeNodes} <span className="text-xl">/ 5</span></p>
          <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">active raft nodes</span><br/>healthy cluster members</h3>
        </div>
        
        <div className="py-12 px-8 flex flex-col items-center justify-center text-center lg:border-l border-[var(--glass-border)]">
          <FiCheckCircle className="text-3xl text-purple-500 mb-4 opacity-80" />
          <p className="text-5xl font-light text-purple-500 mb-3">{totalProcessed >= 1000 ? (totalProcessed/1000).toFixed(1) + 'k' : totalProcessed}</p>
          <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">total processed</span><br/>transactions globally</h3>
        </div>
      </motion.div>

      <div className="grid grid-cols-1 lg:grid-cols-3 border-b border-[var(--glass-border)]">
        {/* Main Dual-Axis Line Chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }} className="lg:col-span-2 p-6 h-[400px] lg:border-r border-[var(--glass-border)] flex flex-col">
          <h3 className="text-lg font-space font-bold mb-6 flex items-center gap-2 shrink-0">
            <FiActivity className="text-[var(--primary)]" /> Throughput vs Latency vs Queue
          </h3>
          <div className="flex-1 min-h-0 w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <LineChart data={timeSeries} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" opacity={0.5} />
                <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickMargin={10} />
                <YAxis yAxisId="left" stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `${v} tx/s`} />
                <YAxis yAxisId="right" orientation="right" stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `${v} ms`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--glass-border)', borderRadius: '12px', backdropFilter: 'blur(10px)' }}
                  itemStyle={{ fontFamily: 'Space Grotesk' }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Line yAxisId="left" type="monotone" name="TPS" dataKey="tps" stroke="var(--primary)" strokeWidth={3} dot={false} isAnimationActive={false} />
                <Line yAxisId="right" type="monotone" name="Latency" dataKey="latency" stroke="#f59e0b" strokeWidth={3} dot={false} isAnimationActive={false} />
                <Line yAxisId="left" type="monotone" name="Queue Size" dataKey="queueSize" stroke="#ec4899" strokeWidth={2} strokeDasharray="5 5" dot={false} isAnimationActive={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Payment Status Insights */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="p-6 h-[400px] flex flex-col">
          <h3 className="text-lg font-space font-bold mb-4 flex items-center gap-2">
            <FiCheckCircle className="text-purple-500" /> Payment Distribution
          </h3>
          <div className="flex-1 flex justify-center items-center">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={5}
                  dataKey="value"
                  isAnimationActive={true}
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--glass-border)', borderRadius: '12px' }}
                  itemStyle={{ fontFamily: 'Space Grotesk' }}
                />
                <Legend verticalAlign="bottom" height={36} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-4 grid grid-cols-3 gap-2 text-center border-t border-[var(--glass-border)] rounded-none pt-4">
             <div>
               <p className="text-xs text-[var(--text-muted)] uppercase">Processed</p>
               <p className="text-lg font-bold text-[#8b5cf6]">{paymentStats.processed}</p>
             </div>
             <div>
               <p className="text-xs text-[var(--text-muted)] uppercase">Failed</p>
               <p className="text-lg font-bold text-red-500">{paymentStats.failed}</p>
             </div>
             <div>
               <p className="text-xs text-[var(--text-muted)] uppercase">Pending</p>
               <p className="text-lg font-bold text-amber-500">{paymentStats.pending}</p>
             </div>
          </div>
        </motion.div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 border-b border-[var(--glass-border)]">
        {/* Node Resource Usage Bar Chart */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.6 }} className="lg:col-span-2 p-6 h-[350px] lg:border-r border-[var(--glass-border)] flex flex-col">
          <h3 className="text-lg font-space font-bold mb-6 flex items-center gap-2 shrink-0">
            <FiServer className="text-blue-500" /> Live Node Utilization
          </h3>
          <div className="flex-1 min-h-0 w-full">
            <ResponsiveContainer width="100%" height="100%" minWidth={1} minHeight={1}>
              <BarChart data={nodeData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }} barGap={8}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" opacity={0.5} />
                <XAxis dataKey="name" stroke="var(--text-muted)" fontSize={12} tickMargin={10} />
                <YAxis yAxisId="left" stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `${v}%`} />
                <YAxis yAxisId="right" orientation="right" stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `${v}MB`} />
                <Tooltip 
                  contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--glass-border)', borderRadius: '12px' }}
                  itemStyle={{ fontFamily: 'Space Grotesk' }}
                  cursor={{ fill: 'var(--glass-border)', opacity: 0.2 }}
                />
                <Legend wrapperStyle={{ paddingTop: '20px' }} />
                <Bar yAxisId="left" name="CPU Usage %" dataKey="cpu" fill="var(--primary)" radius={[4, 4, 0, 0]} isAnimationActive={false} />
                <Bar yAxisId="right" name="Memory Usage MB" dataKey="memory" fill="#3b82f6" radius={[4, 4, 0, 0]} isAnimationActive={false} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>

        {/* Advanced Cluster Insights */}
        <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.7 }} className="p-6 h-[350px]">
          <h3 className="text-lg font-space font-bold mb-6 flex items-center gap-2">
            <FiTrendingUp className="text-emerald-500" /> Raft Consensus Stats
          </h3>
          <div className="space-y-4">
            <div className="p-4 bg-[var(--surface-solid)] bg-opacity-50 rounded-none border border-[var(--glass-border)] rounded-none group hover:border-emerald-500/50 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-sm flex items-center gap-2">
                    <FiServer className="text-emerald-500" /> Current Raft Term
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">Global epoch across nodes</p>
                </div>
                <p className="text-2xl font-bold font-space text-emerald-500">{raftInsights.currentTerm}</p>
              </div>
            </div>

            <div className="p-4 bg-[var(--surface-solid)] bg-opacity-50 rounded-none border border-[var(--glass-border)] rounded-none group hover:border-red-500/50 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-sm flex items-center gap-2">
                    <FiAlertCircle className="text-red-500" /> Leader Elections
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">Total leadership changes</p>
                </div>
                <p className="text-2xl font-bold font-space text-red-500">{raftInsights.leaderChanges}</p>
              </div>
            </div>
            
            <div className="p-4 bg-[var(--surface-solid)] bg-opacity-50 rounded-none border border-[var(--glass-border)] rounded-none group hover:border-blue-500/50 transition-colors">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-sm flex items-center gap-2">
                    <FiActivity className="text-blue-500" /> Global Queue Size
                  </p>
                  <p className="text-xs text-[var(--text-muted)] mt-1">Pending log replications</p>
                </div>
                <p className="text-2xl font-bold font-space text-blue-500">{queueSize}</p>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
      
      {/* Recent Transactions List */}
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.8 }} className="p-6 overflow-hidden flex flex-col">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-space font-bold flex items-center gap-2">
              <FiCheckCircle className="text-purple-500" /> Recent Transactions
            </h3>
            <Link to="/payments" state={{ tab: 'history' }} className="text-xs font-space font-bold uppercase tracking-wider text-[var(--primary)] hover:text-white transition-colors flex items-center gap-1 bg-[var(--primary)]/10 px-3 py-1.5 border border-[var(--primary)]/30 hover:bg-[var(--primary)]">
              View All
            </Link>
          </div>
          <div className="w-full overflow-x-auto">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-[var(--glass-border)] text-xs text-[var(--text-muted)] font-space uppercase tracking-widest">
                  <th className="py-3 px-4 font-normal">Transaction ID</th>
                  <th className="py-3 px-4 font-normal">Date & Time</th>
                  <th className="py-3 px-4 font-normal">Method</th>
                  <th className="py-3 px-4 font-normal">Sender</th>
                  <th className="py-3 px-4 font-normal">Receiver</th>
                  <th className="py-3 px-4 font-normal text-right">Amount</th>
                  <th className="py-3 px-4 font-normal text-center">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentPayments.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-[var(--text-muted)] font-space">
                      No recent transactions.
                    </td>
                  </tr>
                ) : (
                  recentPayments.map((p, idx) => (
                    <tr key={idx} className="border-b border-[var(--glass-border)] last:border-0 hover:bg-[var(--surface-solid)]/30 transition-colors whitespace-nowrap">
                      <td className="py-3 px-4 text-sm font-space" title={p.transaction_id || p.payment_id}>
                        {p.transaction_id || p.payment_id}
                      </td>
                      <td className="py-3 px-4 text-sm font-space">
                        <span className="text-xs text-[var(--text-muted)] opacity-80 bg-[var(--surface-solid)] px-2 py-1 border border-[var(--glass-border)]">
                          {p.created_at ? new Date(p.created_at).toLocaleDateString() : ''} {p.created_at ? new Date(p.created_at).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : ''}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-sm font-space">
                        <div className="flex items-center gap-2">
                          <div className="w-8 flex justify-center">
                            {p.payment_method === 'pm_card_mastercard' ? (
                              <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/mastercard.svg?sanitize=true" className="h-5 object-contain" alt="Mastercard" />
                            ) : p.payment_method === 'pm_card_amex' ? (
                              <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/american-express.svg?sanitize=true" className="h-5 object-contain" alt="Amex" />
                            ) : (
                              <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/visa-alt.svg?sanitize=true" className="h-5 object-contain" alt="Visa" />
                            )}
                          </div>
                          <span className="text-[var(--text-muted)] font-medium">
                            •••• {p.payment_method === 'pm_card_mastercard' ? '4444' : p.payment_method === 'pm_card_amex' ? '0005' : '4242'}
                          </span>
                        </div>
                      </td>
                      <td className="py-3 px-4 text-sm font-space">{p.sender_id}</td>
                      <td className="py-3 px-4 text-sm font-space">{p.receiver_id}</td>
                      <td className="py-3 px-4 text-sm font-space font-bold text-right">
                        {p.amount.toFixed(2)} {p.currency}
                      </td>
                      <td className="py-3 px-4 text-center">
                        <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 text-[10px] font-bold uppercase rounded-none border ${
                          p.status === 'COMPLETED' ? 'bg-green-500/10 text-green-500 border-green-500/30' :
                          p.status === 'FAILED' ? 'bg-red-500/10 text-red-500 border-red-500/30' :
                          'bg-amber-500/10 text-amber-500 border-amber-500/30'
                        }`}>
                          {p.status === 'COMPLETED' ? <FiCheckCircle size={12} /> : p.status === 'FAILED' ? <FiXCircle size={12} /> : <FiClock size={12} />}
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
      </motion.div>
    </div>
  );
}
