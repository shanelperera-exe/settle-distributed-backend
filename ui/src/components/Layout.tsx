import React, { useState, useRef, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { 
  FiSettings, 
  FiDatabase, 
  FiChevronDown,
  FiChevronsRight,
  FiX,
  FiWifi,
  FiServer,
  FiHardDrive,
  FiDollarSign,
  FiTerminal,
  FiMap,
  FiAlertOctagon
} from "react-icons/fi";
import { LuLayoutDashboard, LuLogs } from "react-icons/lu";
import { FaCircleNodes } from "react-icons/fa6";
import { GrTest, GrClearOption } from "react-icons/gr";
import { motion, AnimatePresence } from "framer-motion";
import { useAlerts } from "../contexts/AlertContext";
import type { Alert } from "../contexts/AlertContext";
import LogoImg from "../assets/logos/settle_logo_primary.svg";
import LogoWordGreen from "../assets/logos/logo_word_green.svg";
import { useAuth } from "../contexts/AuthContext";
import { FiLogOut } from "react-icons/fi";
const formatTime = (ts: string) => {
  const d = new Date(ts);
  return d.toLocaleString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const TooltipButton = ({ label, info, onClick, position = "top", align = "center" }: { label: string, info: string, onClick: (label: string, info: string) => void, position?: "top" | "bottom", align?: "left" | "center" | "right" }) => {
  const [show, setShow] = useState(false);
  
  let alignClasses = "left-1/2 -translate-x-1/2";
  let arrowClasses = "left-1/2 -translate-x-1/2";
  
  if (align === "left") {
    alignClasses = "left-0";
    arrowClasses = "left-8";
  } else if (align === "right") {
    alignClasses = "right-0";
    arrowClasses = "right-8";
  }
  
  return (
    <div 
      className="relative flex w-full" 
      onMouseEnter={() => setShow(true)} 
      onMouseLeave={() => setShow(false)}
    >
      <button 
        onClick={() => onClick(label, info)} 
        className="w-full text-left px-4 py-3 rounded-none bg-[var(--background)] hover:bg-[var(--surface)] transition-all text-sm font-medium border border-[var(--glass-border)] hover:border-[var(--primary)] hover:-translate-y-0.5 shadow-sm text-[var(--text)]"
      >
        {label}
      </button>
      <AnimatePresence>
        {show && (
          <motion.div 
            initial={{ opacity: 0, y: position === "top" ? 5 : -5, scale: 0.95 }} 
            animate={{ opacity: 1, y: 0, scale: 1 }} 
            exit={{ opacity: 0, y: position === "top" ? 2 : -2, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={`absolute ${alignClasses} ${position === "top" ? "bottom-full mb-3" : "top-full mt-3"} w-64 bg-[var(--surface)] border border-[var(--glass-border)] text-[var(--text)] text-xs leading-relaxed p-4 shadow-2xl z-[100] pointer-events-none`}
          >
            <div className="font-bold text-[var(--primary)] mb-2 border-b border-[var(--glass-border)] pb-1.5">{label}</div>
            {info}
            <div className={`absolute ${arrowClasses} w-2 h-2 bg-[var(--surface)] border-[var(--glass-border)] rotate-45 ${position === "top" ? "-bottom-[5px] border-b border-r" : "-top-[5px] border-t border-l"}`}></div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const TooltipSelectButton = ({ label, info, onClick, position = "top", align = "center", options, selectedValue, onSelectChange }: { label: string, info: string, onClick: (label: string, info: string) => void, position?: "top" | "bottom", align?: "left" | "center" | "right", options: {label: string, value: string}[], selectedValue: string, onSelectChange: (val: string) => void }) => {
  const [show, setShow] = useState(false);
  
  let alignClasses = "left-1/2 -translate-x-1/2";
  let arrowClasses = "left-1/2 -translate-x-1/2";
  
  if (align === "left") {
    alignClasses = "left-0";
    arrowClasses = "left-8";
  } else if (align === "right") {
    alignClasses = "right-0";
    arrowClasses = "right-8";
  }
  
  return (
    <div 
      className="relative flex w-full group" 
      onMouseEnter={() => setShow(true)} 
      onMouseLeave={() => setShow(false)}
    >
      <div className="w-full flex items-center bg-[var(--background)] group-hover:bg-[var(--surface)] transition-all border border-[var(--glass-border)] group-hover:border-[var(--primary)] group-hover:-translate-y-0.5 shadow-sm text-[var(--text)] text-sm font-medium">
        <button 
          onClick={() => onClick(label, info)} 
          className="flex-1 text-left px-4 py-3 h-full rounded-none"
        >
          {label}
        </button>
        <div className="h-full border-l border-[var(--glass-border)] group-hover:border-[var(--primary)] transition-colors flex items-center bg-[var(--surface-sunken)]">
          <select 
            value={selectedValue}
            onChange={(e) => onSelectChange(e.target.value)}
            className="bg-transparent text-[var(--text)] text-xs font-bold uppercase tracking-widest pl-4 pr-9 py-3 outline-none cursor-pointer appearance-none relative"
            style={{ backgroundImage: `url("data:image/svg+xml;charset=US-ASCII,%3Csvg%20xmlns%3D%22http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg%22%20width%3D%22292.4%22%20height%3D%22292.4%22%3E%3Cpath%20fill%3D%22%23999%22%20d%3D%22M287%2069.4a17.6%2017.6%200%200%200-13-5.4H18.4c-5%200-9.3%201.8-12.9%205.4A17.6%2017.6%200%200%200%200%2082.2c0%205%201.8%209.3%205.4%2012.9l128%20127.9c3.6%203.6%207.8%205.4%2012.8%205.4s9.2-1.8%2012.8-5.4L287%2095c3.5-3.5%205.4-7.8%205.4-12.8%200-5-1.9-9.2-5.5-12.8z%22%2F%3E%3C%2Fsvg%3E")`, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 0.8rem top 50%', backgroundSize: '0.65rem auto' }}
          >
            {options.map(opt => <option key={opt.value} value={opt.value} className="bg-[var(--surface-solid)]">{opt.label}</option>)}
          </select>
        </div>
      </div>
      <AnimatePresence>
        {show && (
          <motion.div 
            initial={{ opacity: 0, y: position === "top" ? 5 : -5, scale: 0.95 }} 
            animate={{ opacity: 1, y: 0, scale: 1 }} 
            exit={{ opacity: 0, y: position === "top" ? 2 : -2, scale: 0.95 }}
            transition={{ duration: 0.15 }}
            className={`absolute ${alignClasses} ${position === "top" ? "bottom-full mb-3" : "top-full mt-3"} w-64 bg-[var(--surface)] border border-[var(--glass-border)] text-[var(--text)] text-xs leading-relaxed p-4 shadow-2xl z-[100] pointer-events-none`}
          >
            <div className="font-bold text-[var(--primary)] mb-2 border-b border-[var(--glass-border)] pb-1.5">{label}</div>
            {info}
            <div className={`absolute ${arrowClasses} w-2 h-2 bg-[var(--surface)] border-[var(--glass-border)] rotate-45 ${position === "top" ? "-bottom-[5px] border-b border-r" : "-top-[5px] border-t border-l"}`}></div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const CornerNav = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [logs, setLogs] = useState<{msg: string, type: 'info' | 'exec' | 'success'}[]>([]);
  const consoleRef = useRef<HTMLDivElement>(null);
  const [selectedNodeToKill, setSelectedNodeToKill] = useState("node-1");

  useEffect(() => {
    if (logs.length === 0) {
      setLogs([
        { msg: `[${new Date().toLocaleTimeString()}] System initialized.`, type: 'info' },
        { msg: `[${new Date().toLocaleTimeString()}] Ready for chaos engineering simulations.`, type: 'info' }
      ]);
    }
  }, []);

  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [logs, isOpen]);

  useEffect(() => {
    if (!isOpen) return;

    let lastLeader = "";
    let lastNodes: string[] = [];

    const interval = setInterval(async () => {
      try {
        const healthRes = await fetch('/api/v1/health/cluster');
        if (!healthRes.ok) return;
        const healthData = await healthRes.json();
        
        const currentNodes: string[] = healthData.cluster_members || [];
        const currentLeader: string = healthData.leader_id || "None";

        if (lastNodes.length > 0) {
          // Check for node drops
          lastNodes.forEach(node => {
            if (!currentNodes.includes(node)) {
              setLogs(prev => [...prev, { msg: `[${new Date().toLocaleTimeString()}] Node ${node} is unreachable.`, type: 'info' }]);
            }
          });

          // Check for node recovery
          currentNodes.forEach(node => {
            if (!lastNodes.includes(node)) {
              setLogs(prev => [...prev, { msg: `[${new Date().toLocaleTimeString()}] Node ${node} joined the cluster.`, type: 'success' }]);
            }
          });
        }

        // Check for leader change
        if (lastLeader && lastLeader !== currentLeader) {
          if (currentLeader === "None") {
            setLogs(prev => [...prev, { msg: `[${new Date().toLocaleTimeString()}] Election in progress...`, type: 'info' }]);
          } else {
            setLogs(prev => [...prev, { msg: `[${new Date().toLocaleTimeString()}] New leader elected: ${currentLeader}`, type: 'success' }]);
          }
        }

        lastLeader = currentLeader;
        lastNodes = currentNodes;
      } catch (err) {
        // Ignore network errors during polling
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [isOpen]);

  const runSimulation = async (label: string, _info: string, specificNode?: string) => {
    setLogs(prev => [...prev, { msg: `[${new Date().toLocaleTimeString()}] Executing: ${label}`, type: 'exec' }]);
    
    try {
      const healthRes = await fetch('/api/v1/health/cluster');
      if (!healthRes.ok) throw new Error("Failed to fetch cluster health");
      const healthData = await healthRes.json();
      const nodes = healthData.cluster_members || [];
      const leader = healthData.leader_id;

      if (nodes.length === 0) {
          throw new Error("No active nodes found in cluster.");
      }

      let target_node = nodes[Math.floor(Math.random() * nodes.length)];
      let scenario = "MOCK_SCENARIO";

      if (label === "Kill Node" && specificNode) {
          scenario = "KILL_NODE";
          target_node = specificNode;
      } else if (label === "Kill Leader Node") {
          scenario = "KILL_NODE";
          if (leader) target_node = leader;
      } else if (label === "Kill Random Follower") {
          scenario = "KILL_NODE";
          const followers = nodes.filter((n: string) => n !== leader);
          if (followers.length > 0) target_node = followers[Math.floor(Math.random() * followers.length)];
      } else if (label === "CPU/Memory Spike") {
          // Randomly pick CPU or Memory
          scenario = Math.random() > 0.5 ? "CPU_SPIKE" : "MEMORY_SPIKE";
      } else if (label === "Graceful Restart") {
          scenario = "GRACEFUL_RESTART";
      } else if (label === "Network Partition") {
          scenario = "NETWORK_PARTITION";
      } else if (label === "Force Election") {
          scenario = "FORCE_ELECTION";
          const followers = nodes.filter((n: string) => n !== leader);
          if (followers.length > 0) target_node = followers[Math.floor(Math.random() * followers.length)];
      } else if (label === "Slow DB Operations") {
          scenario = "DB_DELAY";
      } else if (label === "Simulate Rep. Lag") {
          scenario = "REPLICATION_LAG";
      } else if (label.startsWith("Payment Burst")) {
          scenario = "PAYMENT_BURST";
      } else {
          scenario = label.toUpperCase().replace(/[^A-Z0-9]/g, "_");
      }

      const chaosRes = await fetch('/api/v1/chaos/inject', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ target_node, scenario })
      });

      if (!chaosRes.ok) throw new Error(`Chaos injection failed: ${chaosRes.statusText}`);
      const chaosData = await chaosRes.json();
      
      const type = chaosData.status === "mocked" ? 'info' : 'success';
      setLogs(prev => [...prev, { 
          msg: `[${new Date().toLocaleTimeString()}] ${chaosData.message || 'Simulation triggered on ' + target_node}`, 
          type: type as any
      }]);

    } catch (err: any) {
        setLogs(prev => [...prev, { 
            msg: `[${new Date().toLocaleTimeString()}] Error: ${err.message}`, 
            type: 'info' 
        }]);
    }
  };

  return (
    <>
      <AnimatePresence>
        {!isOpen ? (
          <motion.button 
            key="button"
            layoutId="corner-menu"
            onClick={() => setIsOpen(true)}
            className="group fixed right-4 bottom-4 z-50 h-20 w-20 bg-[var(--surface)] border border-[var(--glass-border)] hover:border-[var(--primary)] shadow-xl rounded-none flex items-center justify-center text-[var(--text)] transition-colors"
          >
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.1 }}>
              <GrTest size={40} className="transition-transform group-hover:scale-110" />
            </motion.div>
          </motion.button>
        ) : (
          <motion.div 
            key="menu"
            layoutId="corner-menu"
            className="fixed right-4 bottom-4 z-[60] w-[95vw] md:w-[48rem] h-[90vh] rounded-none bg-[var(--surface)] flex flex-col shadow-2xl border border-[var(--glass-border)] overflow-hidden text-[var(--text)]"
          >
            <div className="p-6 pb-4 border-b border-[var(--glass-border)] shrink-0 bg-[var(--background)]">
              <div className="text-xs uppercase tracking-widest font-space font-bold opacity-70 mb-1 text-[var(--primary)]">Chaos Engineering</div>
              <h3 className="text-2xl font-bold tracking-tight text-[var(--text)]">Simulation Tools</h3>
            </div>

            {/* Console Area */}
            <div className="h-[40%] flex flex-col shrink-0 border-b border-[var(--glass-border)] bg-[var(--background)]">
              <div className="px-4 py-2 border-b border-[var(--glass-border)] flex items-center justify-between bg-[var(--surface)]">
                <div className="flex items-center gap-2">
                  <FiTerminal className="text-[var(--text-muted)]" />
                  <span className="text-sm font-semibold text-[var(--text)]">Simulation Console</span>
                </div>
                <button 
                  onClick={() => setLogs([{ msg: `[${new Date().toLocaleTimeString()}] Console cleared.`, type: 'info' }])}
                  className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors"
                  title="Clear Console"
                >
                  <GrClearOption size={14} />
                </button>
              </div>
              <div 
                ref={consoleRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-xs flex flex-col gap-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-none [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-[var(--glass-border)]"
              >
                {logs.map((log, i) => (
                  <div key={i} className={`break-words ${
                    log.type === 'info' ? 'text-[var(--text-muted)]' : 
                    log.type === 'exec' ? 'text-blue-500 dark:text-blue-400' : 
                    'text-[var(--primary)]'
                  }`}>{log.msg}</div>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 pt-6 pb-8 flex flex-col gap-8 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-none [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-[var(--glass-border)] hover:[&::-webkit-scrollbar-thumb]:bg-[var(--text-muted)]">
              
              <div>
                <h3 className="text-xl font-bold tracking-tight text-[var(--text)] mb-1">Available Scenarios</h3>
                <p className="text-sm text-[var(--text-muted)]">Select a failure scenario to inject into the active cluster.</p>
              </div>

              {/* Group 1: Node Failures */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3 flex items-center gap-2">
                  <FiServer className="text-[var(--primary)]" />
                  Node Failures
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" position="bottom" onClick={runSimulation} label="Kill Leader Node" info="Instantly terminates the current Raft leader to observe election mechanics." />
                  <TooltipButton align="right" position="bottom" onClick={runSimulation} label="Kill Random Follower" info="Terminates a random non-leader node to test replication resilience." />
                  
                  <TooltipSelectButton 
                    align="left" 
                    position="bottom" 
                    onClick={(l, i) => runSimulation(l, i, selectedNodeToKill)} 
                    label="Kill Node" 
                    info="Terminates the selected node from the dropdown." 
                    options={[1,2,3,4,5].map(n => ({label: `node-${n}`, value: `node-${n}`}))}
                    selectedValue={selectedNodeToKill}
                    onSelectChange={setSelectedNodeToKill}
                  />

                  <TooltipButton align="left" position="bottom" onClick={runSimulation} label="CPU/Memory Spike" info="Simulates a resource exhaustion event on a node to test timeouts and degradation." />
                  <TooltipButton align="right" position="bottom" onClick={runSimulation} label="Graceful Restart" info="Safely restarts a node to test state recovery from the WAL." />
                </div>
              </div>

              {/* Group 2: Network & Connectivity */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3 flex items-center gap-2">
                  <FiWifi className="text-[var(--primary)]" />
                  Network Issues
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" onClick={runSimulation} label="Network Partition" info="Splits the cluster into two isolated sub-networks to test split-brain prevention." />
                </div>
              </div>

              {/* Group 3: Database & Storage */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3 flex items-center gap-2">
                  <FiHardDrive className="text-[var(--primary)]" />
                  Database & Storage
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" onClick={runSimulation} label="Slow DB Operations" info="Exhausts connection pools by injecting artificial latency into database transactions." />
                </div>
              </div>

              {/* Group 4: Consensus & Replication */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3 flex items-center gap-2">
                  <FiDatabase className="text-[var(--primary)]" />
                  Consensus & Replication
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" onClick={runSimulation} label="Force Election" info="Forces a follower to timeout immediately and start a new term." />
                  <TooltipButton align="right" onClick={runSimulation} label="Pause Replication" info="Silently drops all incoming log entries to stall replication." />
                  <TooltipButton align="left" onClick={runSimulation} label="Simulate Rep. Lag" info="Injects network-level delays before processing append-entries." />
                </div>
              </div>

              {/* Group 5: Application & Load */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-[var(--text-muted)] mb-3 flex items-center gap-2">
                  <FiDollarSign className="text-[var(--primary)]" />
                  Application & Load
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" onClick={runSimulation} label="Payment Burst (50 Tx)" info="Fires 50 concurrent payment creation requests to test idempotency and throughput." />
                </div>
              </div>

            </div>

            <motion.button 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ delay: 0.1 }}
              onClick={() => setIsOpen(false)}
              className="absolute right-4 top-5 p-2 text-[var(--text-muted)] hover:text-[var(--text)] transition-colors flex items-center justify-center"
            >
              <FiX size={36} className="font-light" />
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { user } = useAuth();
  
  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--text)] overflow-hidden">
      <Sidebar />
      <ExampleContent children={children} />
      {user?.role === 'admin' && <CornerNav />}
    </div>
  );
};

const Sidebar = () => {
  const [open, setOpen] = useState(true);
  const location = useLocation();
  const { unreadCount } = useAlerts();

  return (
    <motion.nav
      layout
      className="sticky top-0 h-screen shrink-0 bg-[var(--surface)] border-r border-[var(--glass-border)] rounded-none p-3 z-10 flex flex-col items-center rounded-none shadow-none"
      style={{
        width: open ? "240px" : "fit-content",
      }}
    >
      <TitleSection open={open} />

      <div className="flex flex-col gap-3 w-full items-center flex-1 mt-6">
        <Option
          Icon={LuLayoutDashboard}
          title="Dashboard"
          path="/"
          currentPath={location.pathname}
          open={open}
        />
        <Option
          Icon={FiDollarSign}
          title="Payments"
          path="/payments"
          currentPath={location.pathname}
          open={open}
        />
        <Option
          Icon={FaCircleNodes}
          title="Nodes"
          path="/nodes"
          currentPath={location.pathname}
          open={open}
        />
        <Option
          Icon={FiDatabase}
          title="Database"
          path="/database"
          currentPath={location.pathname}
          open={open}
        />
        <Option
          Icon={FiMap}
          title="Architecture"
          path="/architecture"
          currentPath={location.pathname}
          open={open}
        />
        <Option
          Icon={FiAlertOctagon}
          title="Alerts"
          path="/alerts"
          currentPath={location.pathname}
          open={open}
          notifs={unreadCount > 0 ? unreadCount : undefined}
        />
        <Option
          Icon={LuLogs}
          title="Audit Logs"
          path="/audit"
          currentPath={location.pathname}
          open={open}
        />
        <Option
          Icon={FiSettings}
          title="Settings"
          path="/settings"
          currentPath={location.pathname}
          open={open}
        />
      </div>

      <div className="w-full mt-auto">
        <LogoutOption open={open} />
        <ToggleClose open={open} setOpen={setOpen} />
      </div>
    </motion.nav>
  );
};

const LogoutOption = ({ open }: { open: boolean }) => {
  const { logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <motion.button
      layout
      onClick={handleLogout}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className={`relative flex h-12 items-center rounded-none transition-colors mb-2 w-full justify-start text-[var(--text-muted)] hover:bg-red-500/10 hover:text-red-500 ${
        open ? 'px-4' : 'justify-center'
      }`}
    >
      <motion.div layout className="shrink-0 place-content-center text-2xl relative z-10 flex items-center justify-center">
        <FiLogOut />
      </motion.div>
      {open && (
        <motion.span
          layout
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: "auto" }}
          transition={{ delay: 0.125 }}
          className="text-base font-google-code font-bold whitespace-nowrap ml-4 relative z-10"
        >
          Logout
        </motion.span>
      )}
    </motion.button>
  );
};

interface OptionProps {
  Icon: React.ElementType;
  title: string;
  path: string;
  currentPath: string;
  open: boolean;
  notifs?: number | string;
}

const Option = ({ Icon, title, path, currentPath, open, notifs }: OptionProps) => {
  const selected = currentPath === path;
  const navigate = useNavigate();

  return (
    <motion.button
      layout
      onClick={() => navigate(path)}
      whileHover={{ scale: 1.05 }}
      whileTap={{ scale: 0.95 }}
      className={`relative flex h-12 items-center rounded-none transition-colors ${
        open ? 'w-full px-4 justify-start' : 'w-12 justify-center'
      } ${
        !selected 
          ? "bg-transparent hover:bg-[var(--background)] text-[var(--text-muted)] hover:text-[var(--text)]" 
          : "text-black"
      }`}
    >
      <AnimatePresence>
        {selected && (
          <motion.span
            className="absolute inset-0 rounded-none bg-[var(--primary)] shadow-none z-0"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            exit={{ scale: 0 }}
          ></motion.span>
        )}
      </AnimatePresence>

      <motion.div
        layout
        className={`shrink-0 place-content-center text-2xl relative z-10 flex items-center justify-center ${selected ? "text-black" : ""}`}
      >
        <Icon />
        {notifs && (
          <span className="absolute -top-1 -right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-[var(--surface)] shadow-sm"></span>
        )}
      </motion.div>
      {open && (
        <motion.span
          layout
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: "auto" }}
          transition={{ delay: 0.125 }}
          className={`text-base font-google-code font-bold whitespace-nowrap ml-4 relative z-10 flex items-center gap-2.5 ${selected ? "text-black" : ""}`}
        >
          {notifs && (
            <span className="flex h-5 min-w-[20px] items-center justify-center rounded bg-red-500 text-[11px] font-bold text-white px-1.5 shadow-sm">
              {notifs}
            </span>
          )}
          {title}
        </motion.span>
      )}
    </motion.button>
  );
};

const TitleSection = ({ open }: { open: boolean }) => {
  return (
    <div className="border-b border-[var(--glass-border)] rounded-none pb-4 w-full">
      <div className={`flex cursor-pointer items-center transition-colors rounded-none h-12 ${
        open ? "justify-between hover:bg-[var(--background)] px-2" : "justify-center"
      }`}>
        <div className="flex items-center gap-3 h-full">
          <Logo />
          {open && (
            <motion.div
              layout
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.125 }}
            >
              <span className="block text-lg font-bold text-[var(--text)] tracking-tight">Settle</span>
              <span className="block text-[12px] text-[var(--text-muted)] font-bold uppercase tracking-wider">Dev Console</span>
            </motion.div>
          )}
        </div>
        {open && <FiChevronDown className="mr-2 text-[var(--text-muted)]" />}
      </div>
    </div>
  );
};

const Logo = () => {
  return (
    <motion.div
      layout
      className="grid size-12 shrink-0 place-content-center overflow-hidden rounded-none"
    >
      <img src={LogoImg} alt="Settle Logo" className="w-full h-full object-contain" />
    </motion.div>
  );
};

const ToggleClose = ({ open, setOpen }: { open: boolean, setOpen: React.Dispatch<React.SetStateAction<boolean>> }) => {
  return (
    <motion.button
      layout
      onClick={() => setOpen((pv: boolean) => !pv)}
      className="border-t border-[var(--glass-border)] rounded-none transition-colors hover:bg-[var(--background)] w-full rounded-none text-[var(--text-muted)] hover:text-[var(--text)] p-1"
    >
      <div className={`flex items-center p-2 ${open ? "justify-start" : "justify-center"}`}>
        <motion.div
          layout
          className="grid size-12 shrink-0 place-content-center text-2xl"
        >
          <FiChevronsRight
            className={`transition-transform ${open && "rotate-180"}`}
          />
        </motion.div>
        {open && (
          <motion.span
            layout
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.125 }}
            className="text-sm font-google-code font-bold ml-2"
          >
            Hide Sidebar
          </motion.span>
        )}
      </div>
    </motion.button>
  );
};

const ExampleContent: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const { unreadCount, categories, markAsRead } = useAlerts();
  const [isAlertsOpen, setIsAlertsOpen] = useState(false);

  // Flatten all active instances across all rules for the side panel feed
  const activeInstances = React.useMemo(() => {
      const instances: any[] = [];
      categories.forEach(cat => {
          cat.rules.forEach(rule => {
              rule.instances.forEach(inst => {
                  instances.push({ ...inst, ruleName: rule.name });
              });
          });
      });
      // Sort by timestamp descending
      return instances.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
  }, [categories]);

  const getTitle = () => {
    if (location.pathname === "/") return "Dashboard";
    if (location.pathname === "/payments") return "Payments Hub";
    if (location.pathname === "/nodes") return "Nodes";
    if (location.pathname === "/database") return "Database Cluster";
    if (location.pathname === "/architecture") return "System Architecture";
    if (location.pathname === "/alerts") return "System Alerts";
    if (location.pathname === "/audit") return "Audit Logs";
    if (location.pathname === "/settings") return "Settings";
    return "Settle System";
  };

  return (
    <div className="flex-1 flex flex-col h-screen overflow-hidden bg-[var(--background)]">
      <header className="h-[76px] bg-[var(--surface)] border-b border-[var(--glass-border)] rounded-none flex items-center justify-between px-8 shrink-0 z-10 shadow-none transition-colors duration-300">
        <div className="flex flex-col justify-center">
          <h2 className="text-2xl font-google-code font-bold tracking-tight text-[var(--text)]">
            {getTitle()}
          </h2>
          <span className="text-sm text-[var(--text-muted)] font-google-code mt-1">Overview & Metrics</span>
        </div>
        
        <div className="flex items-center gap-5 transition-colors duration-300">
          <div className="relative cursor-pointer hover:bg-[var(--surface-solid)] p-2 rounded-full transition-colors" onClick={() => { setIsAlertsOpen(!isAlertsOpen); markAsRead(); }}>
            <FiAlertOctagon size={24} className="text-[var(--text-muted)] hover:text-[var(--text)] transition-colors" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-red-500 text-[9px] font-bold text-white px-1 shadow-lg border border-[var(--surface)]">
                {unreadCount > 99 ? '99+' : unreadCount}
              </span>
            )}
          </div>
          <div className="h-8 w-[1px] bg-[var(--glass-border)]"></div>
          <img src={LogoWordGreen} alt="Settle Wordmark" className="h-10 object-contain" />
          <div className="h-8 w-[1px] bg-[var(--glass-border)]"></div>
          <div className="flex flex-col justify-center">
            <span className="text-[10px] font-bold tracking-[0.2em] text-[var(--primary)] uppercase leading-none mb-1.5">
              Settle Network
            </span>
            <span className="text-[12px] font-bold tracking-[0.1em] text-[var(--text)] uppercase leading-none">
              Developer Console
            </span>
          </div>
        </div>
      </header>

      <AnimatePresence>
        {isAlertsOpen && (
          <motion.div 
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="absolute top-0 right-0 w-[400px] h-full bg-[var(--surface-solid)] border-l border-[var(--glass-border)] flex flex-col z-50 shadow-2xl"
          >
            <div className="flex justify-between items-center p-4 border-b border-[var(--glass-border)] bg-[var(--surface)]">
              <span className="font-bold flex items-center gap-2 tracking-tight text-lg"><FiAlertOctagon className="text-[var(--primary)]"/> Active Alerts</span>
              <button onClick={() => setIsAlertsOpen(false)} className="hover:text-[var(--primary)] transition-colors"><FiX size={20}/></button>
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {activeInstances.length === 0 ? (
                <div className="text-center text-[var(--text-muted)] mt-10">No active alerts.</div>
              ) : (
                activeInstances.slice(0, 50).map((alert: any) => (
                  <div key={alert.id} className="p-3 bg-[var(--surface)] border border-[var(--glass-border)] text-sm">
                    <div className="flex justify-between items-start mb-1">
                      <span className={`font-bold ${alert.severity === 'error' || alert.severity === 'critical' ? 'text-red-400' : alert.severity === 'warning' ? 'text-orange-400' : 'text-yellow-400'}`}>{alert.ruleName}</span>
                      <span className="text-[10px] text-[var(--text-muted)]">{formatTime(alert.timestamp)}</span>
                    </div>
                    <p className="text-[var(--text-muted)] text-xs">{alert.message}</p>
                  </div>
                ))
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <main className="flex-1 overflow-auto p-8 relative">
        {children}
      </main>
    </div>
  );
};
