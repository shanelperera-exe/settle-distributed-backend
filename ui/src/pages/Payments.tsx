import React, { useState, useEffect, useRef } from 'react';
import { RiArrowRightUpLine } from "react-icons/ri";
import { motion, AnimatePresence } from 'framer-motion';
import { 
  AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer 
} from 'recharts';
import { US, GB, EU } from 'country-flag-icons/react/1x1';
import { FiActivity, FiCheckCircle, FiXCircle, FiClock, FiChevronDown, FiChevronRight, FiLoader } from 'react-icons/fi';
import { MdInsights } from "react-icons/md";
import { TbLocationDollar } from "react-icons/tb";
import { LuHistory, LuDollarSign, LuEuro, LuPoundSterling, LuFilter } from "react-icons/lu";
import { CgPerformance } from "react-icons/cg";
import { FaStripe } from "react-icons/fa";
import { AiOutlineClear } from "react-icons/ai";
import { useLocation } from 'react-router-dom';
import SettleLogo from '../assets/logos/settle_logo_primary.svg';
import SettleLogoWhite from '../assets/logos/settle_logo_primary_white_bg.svg';


// Types
interface TimeSeriesData {
  time: string;
  tps: number;
}

interface Payment {
  payment_id: string;
  transaction_id: string;
  amount: number;
  currency: string;
  status: string;
  sender_id: string;
  receiver_id: string;
  payment_method?: string;
  created_at?: string;
}

interface CustomSelectProps {
  value: string;
  onChange: (val: string) => void;
  options: { label: string; value: string; icon?: React.ReactNode }[];
  align?: 'left' | 'right';
  label?: string;
}

const CustomSelect: React.FC<CustomSelectProps> = ({ value, onChange, options, align = 'left', label }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="flex items-center gap-2">
      {label && <span className="text-xs text-[var(--text-muted)] font-bold uppercase tracking-wider">{label}</span>}
      <div className="relative w-fit" ref={ref}>
        <div 
          className="flex items-center gap-2 cursor-pointer text-[var(--text-muted)] hover:text-[var(--text)] font-space text-sm transition-colors"
          onClick={() => setOpen(!open)}
        >
          {options.find(o => o.value === value)?.icon}
          <span>{options.find(o => o.value === value)?.label || value}</span>
          <FiChevronDown className={`transition-transform duration-200 ${open ? 'rotate-180 text-[var(--text)]' : ''}`} />
        </div>
        
        <AnimatePresence>
          {open && (
            <motion.div
              initial={{ opacity: 0, y: -5 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.15 }}
              className={`absolute top-full ${align === 'right' ? 'right-0' : 'left-0'} mt-2 min-w-[160px] bg-[var(--surface-solid)] border border-[var(--glass-border)] rounded-none shadow-xl z-50 overflow-hidden divide-y divide-[var(--glass-border)]`}
            >
              {options.map((opt) => (
                <div
                  key={opt.value}
                  className={`px-4 py-1.5 flex items-center gap-2 text-sm font-space cursor-pointer transition-colors ${value === opt.value ? 'bg-[var(--primary)]/10 text-[var(--primary)] font-bold' : 'text-[var(--text-muted)] hover:bg-[var(--surface)] hover:text-[var(--text)]'}`}
                  onClick={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                >
                  {opt.icon}
                  {opt.label}
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default function Payments() {
  const location = useLocation();
  const [activeTab, setActiveTab] = useState<'insights' | 'simulate' | 'history'>(location.state?.tab || 'insights');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{status: 'success' | 'error', message: string} | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesData[]>([]);
  const [recentPayments, setRecentPayments] = useState<Payment[]>([]);
  const [paymentStats, setPaymentStats] = useState({ processed: 0, failed: 0, pending: 0, liveTps: 0 });
  const [advancedStats, setAdvancedStats] = useState({
    p50Duration: 0, p95Duration: 0, p99Duration: 0,
    successRate: 0, failRate: 0,
    stripeP95: 0, webhookP95: 0, quorumP95: 0
  });

  // Volume Chart State
  const [volumeMetric, setVolumeMetric] = useState('gross');
  const [timeRange, setTimeRange] = useState('7d');
  const [volumeData, setVolumeData] = useState<any>({
    current_value: 0,
    total_gross_24h: 0,
    timeseries: []
  });

  // Form State
  const [amount, setAmount] = useState('100');
  const [currency, setCurrency] = useState('USD');
  const [senderId, setSenderId] = useState('acc_sim_sender');
  const [receiverId, setReceiverId] = useState('acc_sim_receiver');
  const [cardType, setCardType] = useState('visa');
  const [simMode, setSimMode] = useState<'custom' | 'stripe'>('custom');
  const [currencyDropdownOpen, setCurrencyDropdownOpen] = useState(false);
  const [customDate, setCustomDate] = useState(new Date().toISOString().split('T')[0]);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [metadata, setMetadata] = useState('{\n  "source": "settle_ui_simulation"\n}');
  const [latency, setLatency] = useState('0');
  const [historyFilter, setHistoryFilter] = useState('ALL');
  const [historySort, setHistorySort] = useState('NEWEST');
  const [historyTimeRange, setHistoryTimeRange] = useState('all');
  const [historyCustomDate, setHistoryCustomDate] = useState(new Date().toISOString().split('T')[0]);
  const [historyPage, setHistoryPage] = useState(1);
  const itemsPerPage = 10;
  const [consoleLogs, setConsoleLogs] = useState<{time: string, text: string, color: string}[]>([
    { time: new Date().toLocaleTimeString([], {hour12: false}), text: 'Ready! Your webhook endpoint is receiving events.', color: 'text-black dark:text-gray-400' }
  ]);
  
  const addLog = (text: string, color: string = 'text-black dark:text-gray-200') => {
    setConsoleLogs(prev => [...prev, { time: new Date().toLocaleTimeString([], {hour12: false}), text, color }]);
  };

  const clearConsole = () => {
    setConsoleLogs([{ time: new Date().toLocaleTimeString([], {hour12: false}), text: 'Console cleared.', color: 'text-black dark:text-gray-400' }]);
  };

  useEffect(() => {
    const loadData = () => {
      fetchPayments();
      fetchStats();
      fetchVolumeStats();
    };

    loadData();

    const interval = setInterval(loadData, 5000);

    return () => clearInterval(interval);
  }, [volumeMetric, timeRange, customDate]);

  const fetchVolumeStats = async () => {
    try {
      let url = `/api/v1/payments/stats/volume?metric=${volumeMetric}&time_range=${timeRange}`;
      if (timeRange === 'custom') {
        url += `&custom_date=${customDate}`;
      }
      const res = await fetch(url, {
        headers: {
          'Authorization': `Bearer ${import.meta.env.VITE_API_KEY || 'settle-dev-key-12345'}`
        }
      });
      if (res.ok) {
        const data = await res.json();
        setVolumeData(data);
      }
    } catch (e) {
      console.error('Failed to fetch volume stats', e);
    }
  };

  const fetchPayments = async () => {
    try {
      const res = await fetch('/api/v1/payments/?limit=500', {
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

  const fetchStats = async () => {
    try {
      // Fetch stats from Prometheus
      const statsRes = await Promise.all([
        fetch('/prometheus/api/v1/query?query=sum(payments_processed_total)'),
        fetch('/prometheus/api/v1/query?query=sum(payments_failed_total)'),
        fetch('/prometheus/api/v1/query?query=sum(payments_pending)'),
        fetch('/prometheus/api/v1/query?query=sum(rate(http_requests_total{endpoint=~".*/api/v1/payments.*"}[1m]))'),
        fetch('/prometheus/api/v1/query?query=histogram_quantile(0.50, sum(rate(payment_processing_duration_seconds_bucket[1m])) by (le))'),
        fetch('/prometheus/api/v1/query?query=histogram_quantile(0.95, sum(rate(payment_processing_duration_seconds_bucket[1m])) by (le))'),
        fetch('/prometheus/api/v1/query?query=histogram_quantile(0.99, sum(rate(payment_processing_duration_seconds_bucket[1m])) by (le))'),
        fetch('/prometheus/api/v1/query?query=sum(rate(payments_processed_total{status="success"}[1m]))'),
        fetch('/prometheus/api/v1/query?query=sum(rate(payments_processed_total{status="failure"}[1m]))'),
        fetch('/prometheus/api/v1/query?query=histogram_quantile(0.95, sum(rate(stripe_api_latency_seconds_bucket[1m])) by (le))'),
        fetch('/prometheus/api/v1/query?query=histogram_quantile(0.95, sum(rate(webhook_processing_duration_seconds_bucket[1m])) by (le))'),
        fetch('/prometheus/api/v1/query?query=histogram_quantile(0.95, sum(rate(quorum_commit_latency_seconds_bucket[1m])) by (le))')
      ]);

      const [procData, failData, pendData, tpsData, p50Data, p95Data, p99Data, successRateData, failRateData, stripeP95Data, webhookP95Data, quorumP95Data] = await Promise.all(statsRes.map(res => res.ok ? res.json() : null));
      const processed = parseInt(procData?.data?.result?.[0]?.value?.[1] || "0", 10);
      const failed = parseInt(failData?.data?.result?.[0]?.value?.[1] || "0", 10);
      const pendingRaw = parseInt(pendData?.data?.result?.[0]?.value?.[1] || "0", 10);
      const pending = Math.max(0, pendingRaw);
      
      let tps = 0;
      const tpsVal = tpsData?.data?.result?.[0]?.value?.[1];
      if (tpsVal) {
        tps = parseFloat(tpsVal);
      }

      setPaymentStats({ processed, failed, pending, liveTps: Number(tps.toFixed(2)) });

      const parseMetric = (data: any, multiplier=1) => {
        const val = parseFloat(data?.data?.result?.[0]?.value?.[1] || "0");
        return isNaN(val) ? 0 : val * multiplier;
      };

      setAdvancedStats({
        p50Duration: parseMetric(p50Data, 1000),
        p95Duration: parseMetric(p95Data, 1000),
        p99Duration: parseMetric(p99Data, 1000),
        successRate: parseMetric(successRateData),
        failRate: parseMetric(failRateData),
        stripeP95: parseMetric(stripeP95Data, 1000),
        webhookP95: parseMetric(webhookP95Data, 1000),
        quorumP95: parseMetric(quorumP95Data, 1000)
      });

      // Update timeseries
      const now = new Date();
      const timeStr = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
      
      setTimeSeries(prev => {
        const newData = [...prev, { time: timeStr, tps: Number(tps.toFixed(2)) }];
        if (newData.length > 20) return newData.slice(newData.length - 20);
        return newData;
      });

    } catch (e) {
      console.error('Failed to fetch stats', e);
    }
  };

  const generateId = () => typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).substring(2, 15);

  const simulatePayment = async () => {
    setLoading(true);
    setResult(null);
    
    const idempotencyKey = generateId();
    
    addLog(`--> payment_intent.created [${idempotencyKey.substring(0, 8)}]`, 'text-[#0570de] dark:text-blue-400');
    addLog(`Creating payment of ${amount} ${currency} for ${senderId}...`, 'text-black dark:text-gray-400');

    if (latency && Number(latency) > 0) {
      addLog(`Injecting artificial latency: ${latency}ms...`, 'text-yellow-600 dark:text-yellow-400');
      await new Promise(r => setTimeout(r, Number(latency)));
    }
    
    if (metadata && metadata !== '{}' && metadata !== '{\n  "source": "settle_ui_simulation"\n}') {
      addLog(`Injecting metadata payload...`, 'text-black dark:text-gray-400');
    }

    try {
      const res = await fetch('/api/v1/payments/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'idempotency-key': idempotencyKey,
          'Authorization': `Bearer ${import.meta.env.VITE_API_KEY || 'settle-dev-key-12345'}`
        },
        body: JSON.stringify({
          amount: parseFloat(amount),
          currency,
          sender_id: senderId,
          receiver_id: receiverId,
          payment_method: `pm_card_${cardType}`
        })
      });

      if (res.ok) {
        const data = await res.json();
        addLog(`<--  [200 OK] payment_intent.succeeded [${data.payment_id}]`, 'text-green-600 dark:text-green-400');
        addLog(`Backend processed payment successfully. Idempotency Key: ${idempotencyKey}`, 'text-black dark:text-gray-400');
        setResult({ status: 'success', message: `Payment dispatched successfully! ID: ${data.payment_id}` });
        fetchPayments(); // Refresh table immediately
        setTimeout(() => setResult(null), 3000);
      } else {
        const err = await res.json();
        const errorMsg = typeof err.detail === 'string' ? err.detail : (err.detail ? JSON.stringify(err.detail) : 'Unknown error');
        addLog(`<--  [${res.status} Error] payment_intent.failed`, 'text-red-600 dark:text-red-400');
        addLog(`Backend error: ${errorMsg}`, 'text-red-600 dark:text-red-400');
        setResult({ status: 'error', message: errorMsg || 'Failed to dispatch payment' });
      }
    } catch (e) {
      addLog(`<--  [Network Error] connection failed`, 'text-red-600 dark:text-red-400');
      setResult({ status: 'error', message: 'Network error connecting to cluster.' });
    } finally {
      setLoading(false);
    }
  };

  const processedPayments = React.useMemo(() => {
    let result = [...recentPayments];
    
    if (historyFilter !== 'ALL') {
      result = result.filter(p => p.status === historyFilter);
    }
    
    if (historyTimeRange !== 'all') {
      const now = new Date();
      result = result.filter(p => {
        if (!p.created_at) return true;
        const d = new Date(p.created_at);
        const diffHours = (now.getTime() - d.getTime()) / (1000 * 60 * 60);
        if (historyTimeRange === 'today') return diffHours <= 24;
        if (historyTimeRange === '7d') return diffHours <= 24 * 7;
        if (historyTimeRange === '30d') return diffHours <= 24 * 30;
        if (historyTimeRange === 'custom') {
          return d.toISOString().split('T')[0] === historyCustomDate;
        }
        return true;
      });
    }
    
    // Default sorting is NEWEST (descending by date)
    result.sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA;
    });

    if (historySort === 'HIGHEST') {
      result.sort((a, b) => b.amount - a.amount);
    } else if (historySort === 'LOWEST') {
      result.sort((a, b) => a.amount - b.amount);
    } else if (historySort === 'OLDEST') {
      result.reverse();
    }
    
    return result;
  }, [recentPayments, historyFilter, historySort, historyTimeRange, historyCustomDate]);

  useEffect(() => {
    setHistoryPage(1);
  }, [historyFilter, historySort, historyTimeRange, historyCustomDate]);

  const paginatedPayments = React.useMemo(() => {
    const startIndex = (historyPage - 1) * itemsPerPage;
    return processedPayments.slice(startIndex, startIndex + itemsPerPage);
  }, [processedPayments, historyPage]);

  const totalPages = Math.max(1, Math.ceil(processedPayments.length / itemsPerPage));

  return (
    <div className="space-y-8 pb-12">
      {/* Tabs Navigation */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <SlideTabs activeTab={activeTab} setActiveTab={setActiveTab} />
        <a 
          href="https://dashboard.stripe.com/test/payments" 
          target="_blank" 
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 px-5 h-[44px] bg-[#635BFF] text-white font-space font-bold text-md uppercase hover:bg-[#4d45d6] transition-colors rounded-none w-fit mb-6"
        >
          <FaStripe className="text-5xl ml-1" />
          <span>Dashboard</span>
          <RiArrowRightUpLine className="text-3xl" />
        </a>
      </div>
      <AnimatePresence mode="wait">
        {activeTab === 'insights' && (
          <motion.div 
            key="insights"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="w-full"
          >
            {/* Redesigned Grid-Line Stats Block */}
            <div className="grid grid-cols-1 lg:grid-cols-4 border-y border-[var(--glass-border)]">
              <div className="py-12 px-8 flex flex-col items-center justify-center text-center relative">
                <FiCheckCircle className="text-3xl text-green-500 mb-4 opacity-80" />
                <p className="text-5xl font-light text-green-500 mb-3">{paymentStats.processed >= 1000 ? (paymentStats.processed/1000).toFixed(1) + 'k' : paymentStats.processed}</p>
                <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">total payments processed</span><br/>across the network</h3>
              </div>
              
              <div className="py-12 px-8 flex flex-col items-center justify-center text-center lg:border-l border-[var(--glass-border)]">
                <FiXCircle className="text-3xl text-red-500 mb-4 opacity-80" />
                <p className="text-5xl font-light text-red-500 mb-3">{paymentStats.failed}</p>
                <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">failed transactions</span><br/>detected by system</h3>
              </div>

              <div className="py-12 px-8 flex flex-col items-center justify-center text-center lg:border-l border-[var(--glass-border)]">
                <FiClock className="text-3xl text-amber-500 mb-4 opacity-80" />
                <p className="text-5xl font-light text-amber-500 mb-3">{paymentStats.pending}</p>
                <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">pending transactions</span><br/>awaiting settlement</h3>
              </div>
              
              <div className="py-12 px-8 flex flex-col items-center justify-center text-center lg:border-l border-[var(--glass-border)]">
                <FiActivity className="text-3xl text-[#0570de] dark:text-[#3b82f6] mb-4 opacity-80" />
                <p className="text-5xl font-light text-[#0570de] dark:text-[#3b82f6] mb-3">{paymentStats.liveTps}</p>
                <h3 className="text-[var(--text-muted)] text-base font-light"><span className="text-[var(--text)] font-medium">average network tps</span><br/>during peak hours</h3>
              </div>
            </div>



            {/* Massive KPI Block */}
            <div className="py-12 px-6 flex flex-col items-center justify-center relative overflow-hidden border-b border-[var(--glass-border)]">
              <h3 className="text-lg text-[var(--text-muted)] font-space uppercase tracking-widest mb-2 z-10">Total Financial Volume (24h)</h3>
              <div className="text-6xl font-light text-[var(--text)] z-10">
                <span className="text-green-500">$</span>
                {volumeData.total_gross_24h.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
              </div>
            </div>

            {/* Stripe-style Volume Chart */}
            <div className="p-6 h-[450px] flex flex-col border-b border-[var(--glass-border)]">
              <div className="flex flex-col sm:flex-row justify-between items-start mb-8 gap-4">
                <div className="flex gap-4">
                  <div className="flex flex-col">
                    <CustomSelect 
                      value={volumeMetric}
                      onChange={setVolumeMetric}
                      options={[
                        { label: 'Gross volume', value: 'gross' },
                        { label: 'Net volume', value: 'net' },
                        { label: 'Successful payments', value: 'successful' }
                      ]}
                    />
                    <div className="mt-2 text-3xl font-light">
                      {volumeMetric !== 'successful' && <span className="text-[var(--text-muted)]">$</span>}
                      {volumeData.current_value.toLocaleString(undefined, { minimumFractionDigits: volumeMetric !== 'successful' ? 2 : 0, maximumFractionDigits: 2 })}
                    </div>
                    <div className="mt-1 text-xs text-[var(--text-muted)]">
                      {new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                  
                  <div className="flex flex-col ml-8">
                    <CustomSelect 
                      value={timeRange}
                      onChange={setTimeRange}
                      options={[
                        { label: 'Today', value: 'today' },
                        { label: 'Yesterday', value: 'yesterday' },
                        { label: 'Last 7 days', value: '7d' },
                        { label: 'Last 30 days', value: '30d' },
                        { label: 'Custom date', value: 'custom' }
                      ]}
                    />
                    {timeRange === 'custom' && (
                      <div className="mt-2">
                        <input 
                          type="date" 
                          value={customDate}
                          onChange={(e) => setCustomDate(e.target.value)}
                          className="bg-transparent border border-[var(--glass-border)] rounded-md text-[var(--text)] font-space text-sm px-2 py-1 focus:outline-none focus:border-[var(--primary)] w-full"
                        />
                      </div>
                    )}
                    <div className="mt-2 text-xl font-light text-[var(--text-muted)] opacity-50">
                      {volumeMetric !== 'successful' && <span>$</span>}
                      {volumeData.previous_value?.toLocaleString(undefined, { minimumFractionDigits: volumeMetric !== 'successful' ? 2 : 0, maximumFractionDigits: 2 }) || '0.00'}
                    </div>
                  </div>
                </div>
              </div>
              
              <div className="flex-1 min-h-0 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={volumeData.timeseries} margin={{ top: 10, right: 0, left: 0, bottom: 0 }}>
                    <defs>
                      <linearGradient id="colorVolume" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.1}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--glass-border)" opacity={0.3} />
                    <XAxis 
                      dataKey="time" 
                      stroke="var(--text-muted)" 
                      fontSize={11} 
                      tickLine={false}
                      axisLine={{ stroke: 'var(--glass-border)' }}
                      tickMargin={10} 
                      minTickGap={20}
                    />
                    <Tooltip 
                      contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--glass-border)', borderRadius: '8px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}
                      itemStyle={{ color: 'var(--text)', fontFamily: 'Space Grotesk' }}
                      cursor={{ stroke: 'var(--glass-border)', strokeWidth: 1, strokeDasharray: '3 3' }}
                      formatter={(value: any) => [volumeMetric === 'successful' ? value : `$${Number(value).toFixed(2)}`, volumeMetric === 'gross' ? 'Gross Volume' : volumeMetric === 'net' ? 'Net Volume' : 'Payments']}
                    />
                    <Area 
                      type="monotone" 
                      dataKey="value" 
                      stroke="#8b5cf6" 
                      fillOpacity={1} 
                      fill="url(#colorVolume)" 
                      strokeWidth={2} 
                      isAnimationActive={true} 
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Restored Live Payment Volume Chart */}
            <div className="p-6 h-[400px] flex flex-col border-b border-[var(--glass-border)]">
              <h3 className="text-xl font-space font-bold mb-6 flex items-center gap-2">
                <FiActivity className="text-[var(--primary)]" /> Live Payment Volume
              </h3>
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={timeSeries} margin={{ top: 30, right: 30, left: 40, bottom: 20 }}>
                  <defs>
                    <linearGradient id="colorTps" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="var(--primary)" stopOpacity={0.8}/>
                      <stop offset="95%" stopColor="var(--primary)" stopOpacity={0}/>
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--glass-border)" opacity={0.5} />
                  <XAxis dataKey="time" stroke="var(--text-muted)" fontSize={12} tickMargin={10} label={{ value: 'Time', position: 'insideBottom', offset: -15, fill: 'var(--text-muted)', fontSize: 13 }} />
                  <YAxis stroke="var(--text-muted)" fontSize={12} tickFormatter={(v) => `${v} tx/s`} label={{ value: 'Transactions Per Second (TPS)', angle: -90, position: 'insideLeft', offset: -25, dy: 40, fill: 'var(--text-muted)', fontSize: 13 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: 'var(--surface)', borderColor: 'var(--glass-border)', borderRadius: '12px' }}
                    itemStyle={{ fontFamily: 'Space Grotesk' }}
                  />
                  <Area type="monotone" name="TPS" dataKey="tps" stroke="var(--primary)" fillOpacity={1} fill="url(#colorTps)" strokeWidth={3} isAnimationActive={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            {/* Advanced Latency and KPI Section */}
            <div className="grid grid-cols-1 lg:grid-cols-2 border-b border-[var(--glass-border)] mb-12">
              {/* Left Column: Latency Distribution */}
              <div className="p-6 flex flex-col lg:border-r border-[var(--glass-border)]">
                <div>
                  <h3 className="text-xl font-space font-bold mb-4 flex items-center gap-2">
                    <FiClock className="text-[var(--primary)]" /> Processing Latency
                  </h3>
                  <p className="text-sm text-[var(--text-muted)] mb-6">End-to-end payment processing latency percentiles across the cluster.</p>
                </div>
                
                <div className="grid grid-cols-3 gap-4">
                  <div className="p-4 border border-[var(--glass-border)] flex flex-col items-center justify-center bg-[var(--surface-solid)]/30">
                    <span className="text-xs font-google-code text-[var(--text-muted)] mb-2">P50</span>
                    <span className={`text-2xl font-light ${advancedStats.p50Duration < 200 ? 'text-green-500' : 'text-amber-500'}`}>{advancedStats.p50Duration.toFixed(1)}<span className="text-sm">ms</span></span>
                  </div>
                  <div className="p-4 border border-[var(--glass-border)] flex flex-col items-center justify-center bg-[var(--surface-solid)]/30">
                    <span className="text-xs font-google-code text-[var(--text-muted)] mb-2">P95</span>
                    <span className={`text-2xl font-light ${advancedStats.p95Duration < 500 ? 'text-amber-500' : 'text-red-500'}`}>{advancedStats.p95Duration.toFixed(1)}<span className="text-sm">ms</span></span>
                  </div>
                  <div className="p-4 border border-[var(--glass-border)] flex flex-col items-center justify-center bg-[var(--surface-solid)]/30">
                    <span className="text-xs font-google-code text-[var(--text-muted)] mb-2">P99</span>
                    <span className={`text-2xl font-light ${advancedStats.p99Duration < 1000 ? 'text-amber-500' : 'text-red-500'}`}>{advancedStats.p99Duration.toFixed(1)}<span className="text-sm">ms</span></span>
                  </div>
                </div>
              </div>

              {/* Right Column: Subsystem & Status KPIs */}
              <div className="p-6 flex flex-col justify-between">
                <div>
                  <h3 className="text-xl font-space font-bold mb-4 flex items-center gap-2">
                    <CgPerformance className="text-[var(--primary)]" /> System Performance
                  </h3>
                  
                  <div className="space-y-4">
                    {/* Subsystem P95s */}
                    <div className="flex justify-between items-center border-b border-[var(--glass-border)] pb-3">
                      <span className="text-sm text-[var(--text-muted)]">Stripe API Latency (P95)</span>
                      <span className="font-google-code">{advancedStats.stripeP95.toFixed(1)} ms</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-[var(--glass-border)] pb-3">
                      <span className="text-sm text-[var(--text-muted)]">Webhook Processing (P95)</span>
                      <span className="font-google-code">{advancedStats.webhookP95.toFixed(1)} ms</span>
                    </div>
                    <div className="flex justify-between items-center border-b border-[var(--glass-border)] pb-3">
                      <span className="text-sm text-[var(--text-muted)]">Raft Quorum Commit (P95)</span>
                      <span className="font-google-code">{advancedStats.quorumP95.toFixed(1)} ms</span>
                    </div>
                    
                    {/* Success/Fail Rate */}
                    <div className="flex justify-between items-center pt-2">
                      <div className="flex flex-col">
                        <span className="text-sm text-[var(--text-muted)] mb-1">Success Rate</span>
                        <span className="text-xl text-green-500 font-light">{advancedStats.successRate.toFixed(1)} <span className="text-sm">tx/s</span></span>
                      </div>
                      <div className="flex flex-col text-right">
                        <span className="text-sm text-[var(--text-muted)] mb-1">Failure Rate</span>
                        <span className="text-xl text-red-500 font-light">{advancedStats.failRate.toFixed(1)} <span className="text-sm">tx/s</span></span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        )}

        {activeTab === 'simulate' && (
          <motion.div 
            key="simulate"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
            className="w-full"
          >
            <div className="flex flex-col xl:flex-row items-stretch w-full">
              {/* Left Side: Forms */}
              <div className="flex flex-col w-full xl:w-[calc(48rem+2rem)] shrink-0">
                <div className="xl:pr-8">
                  <div className="grid grid-cols-2 w-full border border-[var(--glass-border)] mb-8">
              <button 
                onClick={() => setSimMode('custom')}
                className={`relative p-5 flex flex-col items-start justify-between min-h-[160px] w-full border-r border-[var(--glass-border)] transition-all ${simMode === 'custom' ? 'bg-[var(--primary)]' : 'bg-transparent hover:bg-[var(--surface-solid)]'}`}
              >
                <div className="w-full flex justify-between items-start mb-4">
                  <img src={simMode === 'custom' ? SettleLogoWhite : SettleLogo} alt="Settle" className="h-16 object-contain object-left" />
                </div>
                <RiArrowRightUpLine className={`absolute top-1 right-1 text-6xl ${simMode === 'custom' ? 'text-white' : 'text-[var(--text-muted)]'}`} />
                <span className={`text-xl font-space font-bold ${simMode === 'custom' ? 'text-white' : 'text-[var(--text)]'}`}>
                  Checkout with Settle
                </span>
              </button>
              
              <button 
                onClick={() => setSimMode('stripe')}
                className={`relative p-5 flex flex-col items-start justify-between min-h-[160px] w-full transition-all ${simMode === 'stripe' ? 'bg-[#635BFF]' : 'bg-transparent hover:bg-[var(--surface-solid)]'}`}
              >
                <div className="w-full flex justify-between items-start mb-4">
                  <img src={simMode === 'stripe' ? "https://cdn.brandfetch.io/idxAg10C0L/theme/light/logo.svg?c=1dxbfHSJFAPEGdCLU4o5B" : "https://cdn.brandfetch.io/idxAg10C0L/theme/dark/logo.svg?c=1dxbfHSJFAPEGdCLU4o5B"} alt="Stripe" className="h-16 object-contain object-left -translate-x-3" />
                </div>
                <RiArrowRightUpLine className={`absolute top-1 right-1 text-6xl ${simMode === 'stripe' ? 'text-white' : 'text-[var(--text-muted)]'}`} />
                <span className={`text-xl font-space font-bold ${simMode === 'stripe' ? 'text-white' : 'text-[var(--text)]'}`}>
                  Checkout with Stripe
                </span>
              </button>
            </div>
            </div>

            <hr className="w-full border-t border-[var(--glass-border)]" />

            <div className="xl:pr-8 mt-8 w-full">
            {simMode === 'custom' ? (
              <div className="bg-transparent p-6 md:p-8 w-full max-w-3xl">
                <div className="flex flex-col mb-6 relative z-10">
                  <h3 className="text-3xl font-space font-bold flex items-center gap-2 text-[var(--text)]">
                    <TbLocationDollar className="text-[var(--primary)]" /> Simulate Payment
                  </h3>
                  <p className="text-sm text-[var(--text-muted)] font-space mt-1">Test your custom integration with live-like simulated responses.</p>
                </div>

                <div className="space-y-5 relative z-10">
                  <div className="space-y-3">
                    <label className="flex items-center text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">
                      Select Payment Method
                    </label>
                    <div className="grid grid-cols-3 gap-0 border border-[var(--glass-border)]">
                      <button onClick={() => setCardType('visa')} className={`flex flex-col items-center justify-center py-4 border-r border-[var(--glass-border)] transition-colors ${cardType === 'visa' ? 'bg-[var(--primary)]/10 opacity-100 grayscale-0' : 'bg-transparent opacity-40 grayscale hover:opacity-100 hover:grayscale-0 hover:bg-[var(--text)]/5'}`}>
                        <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/visa-alt.svg?sanitize=true" className="h-8 object-contain mb-1" alt="Visa" />
                        <span className={`text-[10px] font-bold uppercase tracking-widest ${cardType === 'visa' ? 'text-[var(--primary)]' : 'text-[var(--text)]'}`}>Visa</span>
                      </button>
                      <button onClick={() => setCardType('mastercard')} className={`flex flex-col items-center justify-center py-4 border-r border-[var(--glass-border)] transition-colors ${cardType === 'mastercard' ? 'bg-[var(--primary)]/10 opacity-100 grayscale-0' : 'bg-transparent opacity-40 grayscale hover:opacity-100 hover:grayscale-0 hover:bg-[var(--text)]/5'}`}>
                        <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/mastercard.svg?sanitize=true" className="h-8 object-contain mb-1" alt="Mastercard" />
                        <span className={`text-[10px] font-bold uppercase tracking-widest ${cardType === 'mastercard' ? 'text-[var(--primary)]' : 'text-[var(--text)]'}`}>Mastercard</span>
                      </button>
                      <button onClick={() => setCardType('amex')} className={`flex flex-col items-center justify-center py-4 transition-colors ${cardType === 'amex' ? 'bg-[var(--primary)]/10 opacity-100 grayscale-0' : 'bg-transparent opacity-40 grayscale hover:opacity-100 hover:grayscale-0 hover:bg-[var(--text)]/5'}`}>
                        <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/american-express.svg?sanitize=true" className="h-8 object-contain mb-1" alt="Amex" />
                        <span className={`text-[10px] font-bold uppercase tracking-widest ${cardType === 'amex' ? 'text-[var(--primary)]' : 'text-[var(--text)]'}`}>Amex</span>
                      </button>
                    </div>
                  </div>
                  
                  <div className="space-y-3">
                    <label className="flex items-center text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">
                      Card Details
                    </label>
                    <div className="flex flex-col gap-3">
                      <div className="flex items-center border border-[var(--glass-border)] focus-within:border-[var(--text)] transition-colors">
                        <div className="px-2 border-r border-[var(--glass-border)] h-full flex items-center min-w-[60px] justify-center py-2">
                          <img src={cardType === 'visa' ? "https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/visa-alt.svg?sanitize=true" : cardType === 'mastercard' ? "https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/mastercard.svg?sanitize=true" : "https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/american-express.svg?sanitize=true"} className="h-7 object-contain" alt="Card" />
                        </div>
                        <input 
                          type="text" 
                          readOnly 
                          value={cardType === 'amex' ? "••••  ••••••  •0005" : cardType === 'mastercard' ? "••••  ••••  ••••  4444" : "••••  ••••  ••••  4242"} 
                          className="w-full bg-transparent px-4 py-3 outline-none text-lg font-space font-bold text-[var(--text)] cursor-not-allowed tracking-widest" 
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-3">
                        <div className="border border-[var(--glass-border)] px-4 py-3 flex items-center">
                          <span className="text-[var(--text-muted)] font-space font-bold tracking-widest text-base">12 / 28</span>
                        </div>
                        <div className="border border-[var(--glass-border)] px-4 py-3 flex items-center">
                          <span className="text-[var(--text-muted)] font-space font-bold tracking-widest text-base">•••</span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-3 gap-3">
                    <div className="col-span-2 space-y-3">
                      <label className="block text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">Amount</label>
                      <div className="relative">
                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[var(--text-muted)] text-xl">{currency === 'USD' ? <LuDollarSign /> : currency === 'EUR' ? <LuEuro /> : <LuPoundSterling />}</span>
                        <input 
                          type="number" 
                          min="0"
                          value={amount} 
                          onChange={e => setAmount(Number(e.target.value) < 0 ? '0' : e.target.value)} 
                          className="w-full bg-transparent border border-[var(--glass-border)] pl-10 pr-4 py-3 outline-none focus:border-[var(--text)] transition-all text-xl font-space font-bold text-[var(--text)]" 
                        />
                      </div>
                    </div>
                    <div className="relative space-y-3">
                      <label className="block text-xs font-bold text-[var(--text-muted)] uppercase tracking-widest">Currency</label>
                      <div 
                        className="w-full bg-transparent border border-[var(--glass-border)] px-4 py-3 flex items-center justify-between cursor-pointer hover:border-[var(--text)] transition-all h-[52px]"
                        onClick={() => setCurrencyDropdownOpen(!currencyDropdownOpen)}
                      >
                        <div className="flex items-center gap-3">
                          {currency === 'USD' ? <US className="w-6 h-6 rounded-full shadow-none" /> : currency === 'EUR' ? <EU className="w-6 h-6 rounded-full shadow-none" /> : <GB className="w-6 h-6 rounded-full shadow-none" />}
                          <span className="font-space font-bold text-lg text-[var(--text)]">{currency}</span>
                        </div>
                        <FiChevronDown className="text-[var(--text-muted)] text-lg" />
                      </div>
                      
                      <AnimatePresence>
                        {currencyDropdownOpen && (
                          <motion.div 
                            initial={{ opacity: 0, y: -5 }}
                            animate={{ opacity: 1, y: 0 }}
                            exit={{ opacity: 0, y: -5 }}
                            className="absolute top-[80px] left-0 w-full bg-[var(--surface)] border border-[var(--glass-border)] rounded-none rounded-none shadow-none z-20 overflow-hidden"
                          >
                            {['USD', 'EUR', 'GBP'].map(c => (
                              <div 
                                key={c}
                                className="px-4 py-3 flex items-center gap-3 hover:bg-[var(--primary)]/10 cursor-pointer transition-colors"
                                onClick={() => {
                                  setCurrency(c);
                                  setCurrencyDropdownOpen(false);
                                }}
                              >
                                {c === 'USD' ? <US className="w-6 h-6 rounded-full shadow-none" /> : c === 'EUR' ? <EU className="w-6 h-6 rounded-full shadow-none" /> : <GB className="w-6 h-6 rounded-full shadow-none" />}
                                <span className="font-space font-bold text-lg text-[var(--text)]">{c}</span>
                              </div>
                            ))}
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  <div className="pt-4 border-t border-[var(--glass-border)]">
                    <button 
                      onClick={() => setShowAdvanced(!showAdvanced)} 
                      className="w-full flex items-center justify-between py-2 text-xs font-bold text-[var(--text-muted)] hover:text-[var(--text)] uppercase tracking-widest transition-colors"
                    >
                      <span className="flex items-center gap-2">
                        {showAdvanced ? <FiChevronDown className="text-lg" /> : <FiChevronRight className="text-lg" />}
                        Advanced Configuration
                      </span>
                    </button>
                    
                    <AnimatePresence>
                      {showAdvanced && (
                        <motion.div 
                          initial={{ height: 0, opacity: 0 }} 
                          animate={{ height: 'auto', opacity: 1 }} 
                          exit={{ height: 0, opacity: 0 }}
                          className="overflow-hidden"
                        >
                          <div className="pt-4 space-y-4 pb-2">
                            <div className="grid grid-cols-2 gap-3">
                              <div className="space-y-2">
                                <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Sender ID</label>
                                <input type="text" value={senderId} onChange={e => setSenderId(e.target.value)} className="w-full bg-transparent border border-[var(--glass-border)] px-3 py-2 outline-none focus:border-[var(--text)] transition-colors text-sm font-space text-[var(--text)]" />
                              </div>
                              <div className="space-y-2">
                                <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Receiver ID</label>
                                <input type="text" value={receiverId} onChange={e => setReceiverId(e.target.value)} className="w-full bg-transparent border border-[var(--glass-border)] px-3 py-2 outline-none focus:border-[var(--text)] transition-colors text-sm font-space text-[var(--text)]" />
                              </div>
                            </div>
                            
                            <div className="space-y-2">
                              <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest flex justify-between">
                                <span>Simulate Latency (ms)</span>
                                <span>{latency}ms</span>
                              </label>
                              <input 
                                type="range" 
                                min="0" max="5000" step="100" 
                                value={latency} 
                                onChange={e => setLatency(e.target.value)} 
                                className="w-full accent-[var(--primary)]" 
                              />
                            </div>
                            
                            <div className="space-y-2">
                              <label className="block text-[10px] font-bold text-[var(--text-muted)] uppercase tracking-widest">Custom Metadata (JSON)</label>
                              <textarea 
                                value={metadata} 
                                onChange={e => setMetadata(e.target.value)} 
                                rows={3}
                                className="w-full bg-transparent border border-[var(--glass-border)] px-3 py-2 outline-none focus:border-[var(--text)] transition-colors text-xs font-mono text-[var(--text-muted)] resize-none" 
                              />
                            </div>
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>

                  {result && (
                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className={`p-4 rounded-none border flex items-center gap-3 shadow-none ${result.status === 'success' ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800/30' : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800/30'}`}>
                      <div className={`shrink-0 ${result.status === 'success' ? 'text-green-500' : 'text-red-500'}`}>
                        {result.status === 'success' ? <FiCheckCircle size={20} /> : <FiXCircle size={20} />}
                      </div>
                      <div>
                        <h4 className={`text-sm font-bold ${result.status === 'success' ? 'text-green-800 dark:text-green-400' : 'text-red-800 dark:text-red-400'}`}>
                          {result.status === 'success' ? 'Payment Successful' : 'Payment Failed'}
                        </h4>
                        <p className={`text-xs font-space mt-0.5 ${result.status === 'success' ? 'text-green-600 dark:text-green-500/80' : 'text-red-600 dark:text-red-500/80'}`}>
                          {result.message}
                        </p>
                      </div>
                    </motion.div>
                  )}
                </div>

                <button 
                  onClick={simulatePayment}
                  disabled={loading}
                  className={`w-full mt-8 font-space font-bold tracking-widest py-4 px-6 rounded-none transition-colors duration-200 flex items-center justify-center group border text-lg relative ${result?.status === 'success' ? 'text-white bg-green-600 hover:bg-green-700 border-green-600 hover:border-green-700' : 'text-white hover:text-[var(--background)] bg-[var(--primary)] hover:bg-[var(--text)] border-[var(--primary)] hover:border-[var(--text)]'}`}
                >
                  <span className="flex items-center justify-center gap-3">
                    {loading ? (
                      <FiLoader className="text-2xl animate-spin" />
                    ) : result?.status === 'success' ? (
                      <FiCheckCircle className="text-2xl" />
                    ) : (
                      <TbLocationDollar className="text-2xl transition-transform group-hover:scale-110" />
                    )}
                    {loading ? 'DISPATCHING...' : result?.status === 'success' ? 'PAYMENT SUCCESSFUL' : 'DISPATCH PAYMENT'}
                  </span>
                </button>
              </div>
            ) : (
              <div className="bg-white dark:bg-[#1a1a1a] p-0 rounded-none shadow-none flex flex-col md:flex-row max-w-3xl border border-gray-200 dark:border-gray-800 overflow-hidden font-sans">
                {/* Stripe Checkout Mock - Left Side */}
                <div className="bg-[#f6f9fc] dark:bg-[#111111] w-full md:w-[40%] p-8 border-r border-gray-200 dark:border-gray-800 flex flex-col">
                  <div className="flex items-center gap-2 mb-8">
                    <div className="w-8 h-8 bg-blue-600 rounded-none flex items-center justify-center text-white font-bold">S</div>
                    <span className="font-bold text-gray-800 dark:text-gray-200">Settle Test Inc.</span>
                  </div>
                  <div className="text-gray-500 dark:text-gray-400 text-sm mb-2">Custom Payment</div>
                  <div className="flex items-center border-b-2 border-blue-600 pb-1 mb-8 mt-4 w-max">
                    <span className="text-4xl font-bold text-gray-900 dark:text-white mr-2">
                      {currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£'}
                    </span>
                    <input 
                      type="number" 
                      min="0"
                      value={amount} 
                      onChange={(e) => setAmount(Number(e.target.value) < 0 ? '0' : e.target.value)} 
                      className="text-4xl font-bold text-gray-900 dark:text-white w-32 outline-none bg-transparent"
                    />
                    <select 
                      value={currency} 
                      onChange={(e) => setCurrency(e.target.value)} 
                      className="ml-2 text-xl font-medium text-gray-500 dark:text-gray-400 outline-none bg-transparent cursor-pointer"
                    >
                      <option value="USD">USD</option>
                      <option value="EUR">EUR</option>
                      <option value="GBP">GBP</option>
                    </select>
                  </div>
                  
                  <div className="mt-auto pt-8 flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400 font-medium">
                    <span>Powered by</span>
                    <span className="font-bold text-gray-800 dark:text-gray-200 text-sm tracking-tighter">stripe</span>
                  </div>
                </div>

                {/* Stripe Checkout Mock - Right Side */}
                <div className="bg-white dark:bg-[#1a1a1a] w-full md:w-[60%] p-8">
                  <div className="mb-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Contact</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Email address</label>
                        <input type="email" value={senderId} onChange={e => setSenderId(e.target.value)} className="w-full bg-white dark:bg-[#111111] border border-gray-300 dark:border-gray-700 rounded-none px-3 py-2.5 shadow-none outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500" placeholder="you@example.com" />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Receiver ID</label>
                        <input type="text" value={receiverId} onChange={e => setReceiverId(e.target.value)} className="w-full bg-white dark:bg-[#111111] border border-gray-300 dark:border-gray-700 rounded-none px-3 py-2.5 shadow-none outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500" placeholder="Destination account" />
                      </div>
                    </div>
                  </div>

                  <div className="mb-6">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">Payment</h3>
                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Card information</label>
                        <div className="border border-gray-300 dark:border-gray-700 rounded-none shadow-none overflow-hidden bg-white dark:bg-[#111111] focus-within:ring-1 focus-within:ring-blue-500 focus-within:border-blue-500 transition-shadow">
                          <div className="px-3 py-2.5 border-b border-gray-200 dark:border-gray-700 flex items-center bg-white dark:bg-[#111111]">
                            <input type="text" placeholder="Card number" className="w-full outline-none bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500" />
                            <div className="flex gap-1">
                              <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/visa-alt.svg?sanitize=true" className="h-4" alt="Visa" />
                              <img src="https://raw.githubusercontent.com/datatrans/payment-logos/master/assets/cards/mastercard.svg?sanitize=true" className="h-4" alt="Mastercard" />
                            </div>
                          </div>
                          <div className="flex bg-white dark:bg-[#111111]">
                            <input type="text" placeholder="MM / YY" className="w-1/2 px-3 py-2.5 outline-none bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 border-r border-gray-200 dark:border-gray-700" />
                            <input type="text" placeholder="CVC" className="w-1/2 px-3 py-2.5 outline-none bg-transparent text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500" />
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Name on card</label>
                        <input type="text" className="w-full bg-white dark:bg-[#111111] border border-gray-300 dark:border-gray-700 rounded-none px-3 py-2.5 shadow-none outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500" />
                      </div>
                      
                      <div>
                        <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Country or region</label>
                        <select className="w-full bg-white dark:bg-[#111111] border border-gray-300 dark:border-gray-700 rounded-none px-3 py-2.5 shadow-none outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500 text-gray-900 dark:text-white">
                          <option>United States</option>
                          <option>United Kingdom</option>
                          <option>European Union</option>
                        </select>
                      </div>
                    </div>
                  </div>

                  {result && (
                    <div className={`p-4 rounded-none mb-6 border ${result.status === 'success' ? 'bg-green-50 dark:bg-green-900/10 text-green-800 dark:text-green-400 border-green-200 dark:border-green-800/30' : 'bg-red-50 dark:bg-red-900/10 text-red-800 dark:text-red-400 border-red-200 dark:border-red-800/30'}`}>
                      <p className="text-sm font-medium">{result.message}</p>
                    </div>
                  )}

                  <button 
                    onClick={simulatePayment}
                    disabled={loading}
                    className="w-full bg-[#0570de] hover:bg-[#0058b8] text-white font-medium py-3.5 rounded-none transition-colors flex items-center justify-center shadow-none disabled:opacity-50 text-lg"
                  >
                    {loading ? (
                      <motion.div animate={{ rotate: 360 }} transition={{ repeat: Infinity, duration: 1, ease: "linear" }}>
                        <FiActivity />
                      </motion.div>
                    ) : (
                      `Pay ${currency === 'USD' ? '$' : currency === 'EUR' ? '€' : '£'}${amount || '0'}.00`
                    )}
                  </button>
                </div>
              </div>
            )}
              </div>
              </div>

              {/* Divider */}
              <div className="hidden xl:block w-px bg-[var(--glass-border)] self-stretch shrink-0"></div>
              <div className="xl:hidden w-full h-px bg-[var(--glass-border)] shrink-0 my-4"></div>

              {/* Right Side: Terminal Console */}
              <div className="flex-1 flex flex-col">
                <div className="xl:pl-8">
                  <div className="bg-transparent px-4 py-1 text-sm overflow-hidden flex flex-col h-[450px] w-full shadow-none rounded-none" style={{ fontFamily: "'Ubuntu Mono', monospace" }}>
                {/* Console header */}
                <div className="flex items-center justify-between mb-1 border-b border-[var(--glass-border)] pb-1 shrink-0">
                  <div className="flex items-center gap-2">
                    <FaStripe className="text-6xl text-[#635BFF] -ml-0.5" />
                    <span className="text-[var(--text-muted)] ml-1 font-space font-medium text-sm">stripe-cli / backend logs</span>
                  </div>
                  <button 
                    onClick={clearConsole} 
                    className="p-1.5 text-[var(--text-muted)] hover:text-[#635BFF] bg-transparent transition-colors"
                    title="Clear Console"
                  >
                    <AiOutlineClear size={18} />
                  </button>
                </div>
                {/* Console body */}
                <div className="flex-1 overflow-y-auto space-y-1.5 flex flex-col-reverse">
                  {consoleLogs.slice().reverse().map((log, i) => (
                    <div key={i} className="flex gap-4 hover:bg-[var(--surface)] px-1 py-0.5 transition-colors break-all rounded-none">
                      <span className="text-[var(--text-muted)] opacity-70 shrink-0 select-none">{log.time}</span>
                      <span className={log.color}>{log.text}</span>
                    </div>
                  ))}
                </div>
              </div>
              </div>
              <hr className="w-full border-t border-[var(--glass-border)] mt-2" />
              </div>
            </div>
          </motion.div>
        )}
        {activeTab === 'history' && (
          <motion.div 
            key="history"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.2 }}
          >
            <div className="p-6 pt-4 glass-card overflow-hidden flex flex-col">
              <div className="flex flex-col md:flex-row md:items-center justify-between mb-6 gap-4">
                <h3 className="text-3xl font-space font-bold flex items-center gap-3">
                  <FiClock className="text-[var(--primary)]" /> Recent Payment History
                </h3>
                <div className="flex flex-wrap items-center gap-6">
                  <div className="flex items-center gap-2">
                    <LuFilter className="text-[var(--text-muted)]" />
                    <CustomSelect 
                      label="Time"
                      value={historyTimeRange}
                      onChange={setHistoryTimeRange}
                      options={[
                        { label: 'All time', value: 'all' },
                        { label: 'Today', value: 'today' },
                        { label: 'Last 7 days', value: '7d' },
                        { label: 'Last 30 days', value: '30d' },
                        { label: 'Custom Date', value: 'custom' }
                      ]}
                    />
                    {historyTimeRange === 'custom' && (
                      <input 
                        type="date" 
                        value={historyCustomDate}
                        onChange={(e) => setHistoryCustomDate(e.target.value)}
                        className="bg-transparent border border-[var(--glass-border)] rounded-none text-[var(--text)] font-space text-sm px-2 py-1 focus:outline-none focus:border-[var(--primary)]"
                      />
                    )}
                  </div>
                  <CustomSelect 
                    label="Status"
                    value={historyFilter}
                    onChange={setHistoryFilter}
                    options={[
                      { label: 'All Statuses', value: 'ALL' },
                      { label: 'Completed', value: 'COMPLETED', icon: <FiCheckCircle className="text-green-500" /> },
                      { label: 'Pending', value: 'PENDING', icon: <FiClock className="text-amber-500" /> },
                      { label: 'Failed', value: 'FAILED', icon: <FiXCircle className="text-red-500" /> }
                    ]}
                  />
                  <CustomSelect 
                    label="Sort"
                    align="right"
                    value={historySort}
                    onChange={setHistorySort}
                    options={[
                      { label: 'Newest First', value: 'NEWEST' },
                      { label: 'Oldest First', value: 'OLDEST' },
                      { label: 'Amount (High to Low)', value: 'HIGHEST' },
                      { label: 'Amount (Low to High)', value: 'LOWEST' }
                    ]}
                  />
                </div>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-[var(--glass-border)] rounded-none whitespace-nowrap">
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase">Transaction ID</th>
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase">Date & Time</th>
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase">Payment Method</th>
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase">Sender</th>
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase">Receiver</th>
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase text-right">Amount</th>
                      <th className="py-3 px-4 text-xs font-google-code text-[var(--text-muted)] uppercase text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paginatedPayments.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-8 text-center text-[var(--text-muted)] font-space">
                          No payments found. Submit a simulated payment or adjust your filters.
                        </td>
                      </tr>
                    ) : (
                      paginatedPayments.map((p, idx) => (
                        <tr key={idx} className="border-b border-[var(--glass-border)] rounded-none hover:bg-[var(--surface-solid)]/30 transition-colors whitespace-nowrap">
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
              
              {processedPayments.length > 0 && (
                <div className="flex items-center justify-between border-t border-[var(--glass-border)] pt-4 mt-2">
                  <span className="text-xs text-[var(--text-muted)] font-space">
                    Showing {((historyPage - 1) * itemsPerPage) + 1} to {Math.min(historyPage * itemsPerPage, processedPayments.length)} of {processedPayments.length} entries
                  </span>
                  <div className="flex items-center gap-2">
                    <button 
                      onClick={() => setHistoryPage(p => Math.max(1, p - 1))}
                      disabled={historyPage === 1}
                      className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider border border-[var(--glass-border)] bg-[var(--surface-solid)] text-[var(--text)] disabled:opacity-30 transition-colors hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] rounded-none"
                    >
                      Prev
                    </button>
                    <div className="flex items-center gap-1">
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                        <button
                          key={page}
                          onClick={() => setHistoryPage(page)}
                          className={`w-7 h-7 flex items-center justify-center text-xs font-bold border border-[var(--glass-border)] rounded-none transition-colors ${
                            historyPage === page 
                              ? 'bg-[var(--primary)] text-white border-[var(--primary)]' 
                              : 'bg-[var(--surface-solid)] text-[var(--text-muted)] hover:bg-[var(--primary)]/10 hover:text-[var(--primary)]'
                          }`}
                        >
                          {page}
                        </button>
                      ))}
                    </div>
                    <button 
                      onClick={() => setHistoryPage(p => Math.min(totalPages, p + 1))}
                      disabled={historyPage === totalPages}
                      className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider border border-[var(--glass-border)] bg-[var(--surface-solid)] text-[var(--text)] disabled:opacity-30 transition-colors hover:bg-[var(--primary)]/10 hover:text-[var(--primary)] rounded-none"
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

const SlideTabs = ({ activeTab, setActiveTab }: { activeTab: string, setActiveTab: (v: any) => void }) => {
  const [position, setPosition] = useState({
    left: 0,
    width: 0,
    opacity: 0,
  });

  const tabs = [
    { id: 'insights', label: 'Payment Insights', icon: <MdInsights className="inline mr-2 mb-0.5" /> },
    { id: 'simulate', label: 'Simulate Payment', icon: <TbLocationDollar className="inline mr-2 mb-0.5" /> },
    { id: 'history', label: 'Payment History', icon: <LuHistory className="inline mr-2 mb-0.5" /> }
  ];

  return (
    <ul
      onMouseLeave={() => {
        setPosition((pv) => ({
          ...pv,
          opacity: 0,
        }));
      }}
      className="relative flex w-fit rounded-none border border-black/20 dark:border-[var(--glass-border)] bg-[var(--surface)] p-1 mb-6"
    >
      {tabs.map((tab) => (
        <Tab 
          key={tab.id} 
          setPosition={setPosition} 
          isActive={activeTab === tab.id}
          onClick={() => setActiveTab(tab.id)}
        >
          {tab.icon}
          {tab.label}
        </Tab>
      ))}

      <Cursor position={position} />
    </ul>
  );
};

const Tab = ({ children, setPosition, isActive, onClick }: any) => {
  const ref = useRef<HTMLLIElement>(null);

  return (
    <li
      ref={ref}
      onMouseEnter={() => {
        if (!ref?.current) return;

        const { width } = ref.current.getBoundingClientRect();

        setPosition({
          left: ref.current.offsetLeft,
          width,
          opacity: 1,
        });
      }}
      onClick={onClick}
      className={`relative z-10 block cursor-pointer px-4 py-2 text-sm uppercase font-space font-bold transition-colors ${
        isActive ? 'text-[var(--primary)]' : 'text-[var(--text-muted)] hover:text-[var(--text)]'
      }`}
    >
      {children}
    </li>
  );
};

const Cursor = ({ position }: { position: any }) => {
  return (
    <motion.li
      animate={{
        ...position,
      }}
      transition={{ type: "spring", stiffness: 400, damping: 30 }}
      className="absolute z-0 h-9 rounded-none bg-[var(--background)] dark:border-[var(--glass-border)]"
    />
  );
};
