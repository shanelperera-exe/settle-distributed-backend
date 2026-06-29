import React, { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  FiChevronDown,
  FiChevronsRight,
  FiDollarSign,
  FiSettings,
  FiDatabase,
} from "react-icons/fi";
import { LuLayoutDashboard } from "react-icons/lu";
import { FaCircleNodes } from "react-icons/fa6";
import { motion, AnimatePresence } from "framer-motion";
import LogoImg from "../assets/logos/settle_logo_primary.svg";
import LogoWordGreen from "../assets/logos/logo_word_green.svg";

export const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return (
    <div className="flex h-screen bg-[var(--background)] text-[var(--text)] overflow-hidden">
      <Sidebar />
      <ExampleContent children={children} />
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
