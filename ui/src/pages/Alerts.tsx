import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AiOutlineAlert } from 'react-icons/ai';
import { FiChevronDown, FiChevronRight, FiAlertCircle, FiAlertTriangle, FiInfo } from 'react-icons/fi';
import { useAlerts } from '../contexts/AlertContext';
import type { AlertCategory, AlertRule, AlertInstance } from '../contexts/AlertContext';

const formatTime = (ts: string) => {
  const d = new Date(ts);
  return d.toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

const RuleItem: React.FC<{ rule: AlertRule }> = ({ rule }) => {
  const [expanded, setExpanded] = useState(false);

  // Determine highest severity for styling the card
  const hasCritical = rule.instances.some(i => i.severity === 'critical');
  const hasError = rule.instances.some(i => i.severity === 'error' || i.severity === 'critical');
  const hasWarning = rule.instances.some(i => i.severity === 'warning');
  
  const accentColor = hasError ? 'border-l-red-500/80' : hasWarning ? 'border-l-orange-500/80' : 'border-l-yellow-500/80';
  const badgeColor = hasError ? 'text-white bg-red-500 border-red-500 shadow-sm' : hasWarning ? 'text-white bg-orange-500 border-orange-500 shadow-sm' : 'text-white bg-yellow-500 border-yellow-500 shadow-sm';
  const Icon = hasError ? FiAlertCircle : hasWarning ? FiAlertTriangle : FiInfo;
  const iconColor = hasError ? 'text-red-500' : hasWarning ? 'text-orange-500' : 'text-yellow-500';

  return (
    <div className={`bg-[var(--surface)] overflow-hidden transition-all duration-300 border-l-[3px] ${accentColor}`}>
      <div 
        className="flex items-center justify-between p-5 cursor-pointer hover:bg-white/5 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-4">
          <span className="text-[var(--text-muted)] transition-transform duration-200">
              {expanded ? <FiChevronDown size={18}/> : <FiChevronRight size={18}/>}
          </span>
          <div className="flex items-center gap-4">
              <Icon className={`${iconColor}`} size={20} />
              <div>
                  <span className="font-google-code text-[15px] text-[var(--text)] font-bold tracking-wide">
                    {rule.name}
                  </span>
              </div>
          </div>
        </div>
        <div className={`px-4 py-1.5 text-[11px] font-bold uppercase tracking-[0.2em] border ${badgeColor}`}>
          {rule.active_count} {rule.active_count === 1 ? 'Instance' : 'Instances'}
        </div>
      </div>
      
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-[var(--glass-border)] bg-[var(--surface-solid)]/30"
          >
            {rule.metadata && Object.keys(rule.metadata).length > 0 && (
              <div className="p-6 pl-[5.5rem] bg-transparent border-b border-[var(--glass-border)]">
                <div className="grid grid-cols-2 gap-y-6 gap-x-8">
                  {Object.entries(rule.metadata).map(([key, value]) => (
                    <div key={key} className="flex flex-col gap-2">
                      <span className="text-[11px] text-[var(--text-muted)] font-google-code uppercase tracking-[0.15em] font-bold">
                        {key}
                      </span>
                      <span className="text-[13px] text-[var(--text)] font-mono whitespace-normal break-words leading-relaxed opacity-90">
                        {value}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
            {rule.instances.map((instance: AlertInstance) => (
              <div key={instance.id} className="p-5 pl-[5.5rem] border-b border-[var(--glass-border)] last:border-b-0 flex justify-between items-start hover:bg-white/5 transition-colors">
                  <div className="max-w-[75%]">
                      <p className={`text-[15px] mb-3 font-medium leading-relaxed ${iconColor}`}>
                          {instance.message}
                      </p>

                      {instance.labels && Object.keys(instance.labels).length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-4 mt-2">
                          {Object.entries(instance.labels).map(([k, v]) => (
                            <div key={k} className="inline-flex items-center rounded-md border border-[var(--glass-border)] bg-[var(--surface-solid)] text-[11px] font-mono shadow-sm overflow-hidden transition-colors hover:border-[var(--primary)]/40 hover:shadow">
                              <span className="px-2 py-1 bg-[var(--glass-border)] text-[var(--text-muted)] font-medium border-r border-[var(--glass-border)] tracking-tight">
                                {k}
                              </span>
                              <span className="px-2.5 py-1 font-semibold text-[var(--text)] tracking-tight opacity-90">
                                {v as React.ReactNode}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}

                      <div className="flex items-center gap-3">
                          <span className="text-[11px] text-[var(--text-muted)] font-google-code uppercase tracking-wider bg-[var(--surface)] px-3 py-1 border border-[var(--glass-border)]">ID: {instance.id.split('-')[0]}</span>
                      </div>
                  </div>
                  <div className="text-[13px] text-[var(--text)] font-mono whitespace-normal break-words leading-relaxed opacity-90">
                      {formatTime(instance.timestamp)}
                  </div>
              </div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

const Alerts: React.FC = () => {
  const { categories, totalActive } = useAlerts();

  return (
    <div className="space-y-8 pb-12">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center justify-between mb-8 border-b border-[var(--glass-border)] pb-6"
      >
        <div className="flex items-center gap-3">
          <div className="text-[var(--primary)]">
            <AiOutlineAlert size={48} />
          </div>
          <div>
            <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">System Alerts</h1>
            <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest">Stateful Prometheus-style Alert Rules</p>
          </div>
        </div>
        
        <div className="px-4 py-2 bg-[var(--surface-solid)] border border-[var(--glass-border)] text-sm font-bold uppercase tracking-wider">
           <span className={totalActive > 0 ? "text-[var(--primary)]" : "text-[var(--text-muted)]"}>
               {totalActive} Firing
           </span>
        </div>
      </motion.div>

      <div className="space-y-8">
        {totalActive === 0 ? (
          <div className="py-24 text-center border border-[var(--glass-border)] bg-[var(--surface)] text-[var(--text-muted)]">
            <AiOutlineAlert size={48} className="mx-auto mb-4 opacity-20" />
            <p className="text-lg font-light">No active alerts</p>
            <p className="text-sm mt-2 opacity-60">System is running normally</p>
          </div>
        ) : (
          <div className="space-y-[1px] bg-[var(--glass-border)]">
          {categories
            .map((cat: AlertCategory) => ({
                ...cat,
                rules: cat.rules.filter((rule: AlertRule) => rule.active_count > 0)
            }))
            .filter(cat => cat.rules.length > 0)
            .map((cat: AlertCategory) => (
                <React.Fragment key={cat.category}>
                   {cat.rules.map((rule: AlertRule) => (
                       <RuleItem key={rule.name} rule={rule} />
                   ))}
                </React.Fragment>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default Alerts;
