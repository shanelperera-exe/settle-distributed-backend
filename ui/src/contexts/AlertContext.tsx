import React, { createContext, useContext, useEffect, useState } from 'react';

export type AlertLevel = 'info' | 'warning' | 'error' | 'success' | 'critical';

export interface AlertInstance {
  id: string;
  message: string;
  severity: AlertLevel;
  labels: Record<string, string>;
  timestamp: string;
}

export interface AlertRule {
  name: string;
  active_count: number;
  instances: AlertInstance[];
  metadata?: Record<string, string>;
}

export interface AlertCategory {
  category: string;
  rules: AlertRule[];
}

interface AlertContextType {
  categories: AlertCategory[];
  totalActive: number;
  unreadCount: number;
  markAsRead: () => void;
}

const AlertContext = createContext<AlertContextType>({
  categories: [],
  totalActive: 0,
  unreadCount: 0,
  markAsRead: () => {}
});

export const useAlerts = () => useContext(AlertContext);

export const AlertProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [categories, setCategories] = useState<AlertCategory[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [totalActive, setTotalActive] = useState(0);

  useEffect(() => {
    let sse: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout>;

    const connectSSE = () => {
      if (sse) {
        sse.close();
      }
      sse = new EventSource("/api/v1/alerts/stream");

      sse.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.categories) {
            setCategories(data.categories);
            
            // Calculate total active
            let currentActive = 0;
            data.categories.forEach((cat: AlertCategory) => {
              cat.rules.forEach((rule: AlertRule) => {
                currentActive += rule.active_count;
              });
            });
            
            setTotalActive(currentActive);
            
            if (data.total_alerts_fired !== undefined) {
               setUnreadCount((prevUnread) => {
                   return prevUnread + (data.total_alerts_fired - ((window as any)._lastTotalAlertsFired || data.total_alerts_fired));
               });
               (window as any)._lastTotalAlertsFired = data.total_alerts_fired;
            }
          }
        } catch (e) {
          console.error("Error parsing alert SSE:", e);
        }
      };

      sse.onerror = (err) => {
        console.error("SSE connection error:", err);
        sse?.close();
        // Retry in 2s
        retryTimeout = setTimeout(connectSSE, 2000);
      };
    };

    connectSSE();

    return () => {
      if (sse) sse.close();
      clearTimeout(retryTimeout);
    };
  }, []);

  const markAsRead = () => {
    setUnreadCount(0);
  };

  return (
    <AlertContext.Provider value={{ categories, totalActive, unreadCount, markAsRead }}>
      {children}
    </AlertContext.Provider>
  );
};
