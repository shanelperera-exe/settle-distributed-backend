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
  FiTerminal
} from "react-icons/fi";
import { LuLayoutDashboard } from "react-icons/lu";
import { FaCircleNodes } from "react-icons/fa6";
import { GrTest, GrClearOption } from "react-icons/gr";
import { motion, AnimatePresence } from "framer-motion";
import LogoImg from "../assets/logos/settle_logo_primary.svg";
import LogoWordGreen from "../assets/logos/logo_word_green.svg";

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
        className="w-full text-left px-4 py-3 rounded-none bg-neutral-900 hover:bg-neutral-800 transition-all text-sm font-medium border border-neutral-800 hover:border-emerald-500/50 hover:-translate-y-0.5 shadow-sm text-neutral-300"
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
            className={`absolute ${alignClasses} ${position === "top" ? "bottom-full mb-3" : "top-full mt-3"} w-64 bg-neutral-950 border border-emerald-500/40 text-neutral-300 text-xs leading-relaxed p-4 shadow-2xl z-[100] pointer-events-none`}
          >
            <div className="font-bold text-emerald-400 mb-2 border-b border-emerald-500/20 pb-1.5">{label}</div>
            {info}
            <div className={`absolute ${arrowClasses} w-2 h-2 bg-neutral-950 border-emerald-500/40 rotate-45 ${position === "top" ? "-bottom-[5px] border-b border-r" : "-top-[5px] border-t border-l"}`}></div>
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
    }, 2000);

    return () => clearInterval(interval);
  }, [isOpen]);

  const runSimulation = async (label: string, _info: string) => {
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

      if (label === "Kill Leader Node") {
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
            className="group fixed right-4 bottom-4 z-50 h-20 w-20 bg-neutral-950 border border-emerald-500/30 hover:border-emerald-500/60 shadow-xl rounded-none flex items-center justify-center text-white transition-colors"
          >
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.1 }}>
              <GrTest size={40} className="transition-transform group-hover:scale-110" />
            </motion.div>
          </motion.button>
        ) : (
          <motion.div 
            key="menu"
            layoutId="corner-menu"
            className="fixed right-4 bottom-4 z-[60] w-[95vw] md:w-[48rem] h-[90vh] rounded-none bg-neutral-950 flex flex-col shadow-2xl border border-emerald-500/30 overflow-hidden text-neutral-200"
          >
            <div className="p-6 pb-4 border-b border-white/5 shrink-0 bg-neutral-900/50">
              <div className="text-xs uppercase tracking-widest font-space font-bold opacity-70 mb-1 text-emerald-400">Chaos Engineering</div>
              <h3 className="text-2xl font-bold tracking-tight text-white">Simulation Tools</h3>
            </div>

            {/* Console Area */}
            <div className="h-[40%] flex flex-col shrink-0 border-b border-white/10 bg-black/60">
              <div className="px-4 py-2 border-b border-white/5 flex items-center justify-between bg-neutral-900/80">
                <div className="flex items-center gap-2">
                  <FiTerminal className="text-neutral-400" />
                  <span className="text-sm font-semibold text-neutral-200">Simulation Console</span>
                </div>
                <button 
                  onClick={() => setLogs([{ msg: `[${new Date().toLocaleTimeString()}] Console cleared.`, type: 'info' }])}
                  className="text-neutral-500 hover:text-white transition-colors"
                  title="Clear Console"
                >
                  <GrClearOption size={14} />
                </button>
              </div>
              <div 
                ref={consoleRef}
                className="flex-1 overflow-y-auto p-4 font-mono text-xs flex flex-col gap-1 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-none [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-white/10"
              >
                {logs.map((log, i) => (
                  <div key={i} className={`break-words ${
                    log.type === 'info' ? 'text-neutral-400' : 
                    log.type === 'exec' ? 'text-blue-400' : 
                    'text-emerald-400'
                  }`}>{log.msg}</div>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 pt-6 pb-8 flex flex-col gap-8 [&::-webkit-scrollbar]:w-1.5 [&::-webkit-scrollbar-thumb]:rounded-none [&::-webkit-scrollbar-track]:bg-transparent [&::-webkit-scrollbar-thumb]:bg-neutral-700 hover:[&::-webkit-scrollbar-thumb]:bg-neutral-600">
              
              <div>
                <h3 className="text-xl font-bold tracking-tight text-white mb-1">Available Scenarios</h3>
                <p className="text-sm text-neutral-400">Select a failure scenario to inject into the active cluster.</p>
              </div>

              {/* Group 1: Node Failures */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-3 flex items-center gap-2">
                  <FiServer className="text-emerald-500" />
                  Node Failures
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" position="bottom" onClick={runSimulation} label="Kill Leader Node" info="Instantly terminates the current Raft leader to observe election mechanics." />
                  <TooltipButton align="right" position="bottom" onClick={runSimulation} label="Kill Random Follower" info="Terminates a random non-leader node to test replication resilience." />
                  <TooltipButton align="left" position="bottom" onClick={runSimulation} label="CPU/Memory Spike" info="Simulates a resource exhaustion event on a node to test timeouts and degradation." />
                  <TooltipButton align="right" position="bottom" onClick={runSimulation} label="Graceful Restart" info="Safely restarts a node to test state recovery from the WAL." />
                </div>
              </div>

              {/* Group 2: Network & Connectivity */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-3 flex items-center gap-2">
                  <FiWifi className="text-emerald-500" />
                  Network Issues
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" onClick={runSimulation} label="Network Partition" info="Splits the cluster into two isolated sub-networks to test split-brain prevention." />
                </div>
              </div>

              {/* Group 3: Database & Storage */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-3 flex items-center gap-2">
                  <FiHardDrive className="text-emerald-500" />
                  Database & Storage
                </h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  <TooltipButton align="left" onClick={runSimulation} label="Slow DB Operations" info="Exhausts connection pools by injecting artificial latency into database transactions." />
                </div>
              </div>

              {/* Group 4: Consensus & Replication */}
              <div>
                <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-3 flex items-center gap-2">
                  <FiDatabase className="text-emerald-500" />
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
                <h4 className="text-xs font-bold uppercase tracking-widest text-neutral-400 mb-3 flex items-center gap-2">
                  <FiDollarSign className="text-emerald-500" />
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
              className="absolute right-4 top-5 p-2 text-neutral-400 hover:text-white transition-colors flex items-center justify-center"
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
  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--text)] overflow-hidden">
      <Sidebar />
      <ExampleContent children={children} />
      <CornerNav />
    </div>
  );
};

const Sidebar = () => {
  const [open, setOpen] = useState(true);
  const location = useLocation();

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
          Icon={FiSettings}
          title="Settings"
          path="/settings"
          currentPath={location.pathname}
          open={open}
        />
      </div>

      <ToggleClose open={open} setOpen={setOpen} />
    </motion.nav>
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
          : "text-white"
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
        className={`shrink-0 place-content-center text-2xl relative z-10 flex items-center justify-center ${selected ? "text-white" : ""}`}
      >
        <Icon />
      </motion.div>
      {open && (
        <motion.span
          layout
          initial={{ opacity: 0, width: 0 }}
          animate={{ opacity: 1, width: "auto" }}
          transition={{ delay: 0.125 }}
          className={`text-base font-google-code font-bold whitespace-nowrap ml-4 relative z-10 ${selected ? "text-white" : ""}`}
        >
          {title}
        </motion.span>
      )}

      {notifs && open && (
        <motion.span
          initial={{ scale: 0, opacity: 0 }}
          animate={{
            opacity: 1,
            scale: 1,
          }}
          style={{ y: "-50%" }}
          transition={{ delay: 0.5 }}
          className="absolute right-2 top-1/2 h-4 w-4 flex items-center justify-center rounded bg-[var(--error)] text-[10px] text-white z-10"
        >
          {notifs}
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
      className="border-t border-[var(--glass-border)] rounded-none transition-colors hover:bg-[var(--background)] w-full mt-auto rounded-none text-[var(--text-muted)] hover:text-[var(--text)] p-1"
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
  const getTitle = () => {
    if (location.pathname === "/") return "Dashboard";
    if (location.pathname === "/payments") return "Payments Hub";
    if (location.pathname === "/nodes") return "Nodes";
    if (location.pathname === "/database") return "Database Cluster";
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

      <main className="flex-1 overflow-auto p-8 relative">
        {children}
      </main>
    </div>
  );
};
