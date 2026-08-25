import { useEffect, useCallback, useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { LiaExternalLinkAltSolid } from "react-icons/lia";
import {
  ReactFlow,
  Controls,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  addEdge,
  useStoreApi
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FiDatabase, FiActivity, FiSmartphone, FiGlobe, FiMap, FiTerminal, FiX } from 'react-icons/fi';
import SettleLogo from '../assets/logos/settle_logo_primary.svg';

// --- Custom Nodes ---

const dispatchLogEvent = (nodeId: string) => {
  window.dispatchEvent(new CustomEvent('open-node-logs', { detail: { nodeId } }));
};

const BaseNode = ({ children, sourcePos = Position.Bottom, targetPos = Position.Top, customSourcePos, customTargetPos, className = "" }: any) => {
  return (
    <div className={`bg-[var(--surface-solid)] p-6 shadow-lg min-w-[240px] flex flex-col items-center justify-center relative backdrop-blur-md border ${className || 'border-[var(--glass-border)]'}`}>
      {targetPos !== null && <Handle type="target" position={customTargetPos || targetPos} className="w-2 h-2 !bg-[var(--primary)] border-none" />}
      {children}
      {sourcePos !== null && <Handle id="bottom" type="source" position={customSourcePos || sourcePos} className="w-2 h-2 !bg-[var(--primary)] border-none" />}
    </div>
  );
};

const ClientNode = ({ data }: any) => (
  <div className="bg-[var(--surface-solid)] border-2 border-[var(--text)] p-6 min-w-[200px] flex flex-col items-center justify-center relative transition-transform hover:scale-105">
    <div className="flex flex-col items-center gap-3 w-full justify-center">
      {data.icon === 'web' ? <FiGlobe size={36} className="text-[var(--primary)]" /> : <FiSmartphone size={36} className="text-[var(--primary)]" />}
      <span className="text-xl font-bold text-[var(--text)] tracking-wider text-center">{data.label}</span>
    </div>
    <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-[var(--primary)] border-none opacity-0" />
  </div>
);

const ExternalNode = ({ data }: any) => (
  <div className="bg-[var(--surface-solid)] border-2 border-[var(--text)] p-6 min-w-[240px] flex flex-col items-center justify-center relative transition-transform hover:scale-105">
    <div className="flex items-center gap-5 w-full">
      <img
        src="https://cdn.brandfetch.io/idxAg10C0L/theme/dark/logo.svg?c=1dxbfHSJFAPEGdCLU4o5B"
        alt="Stripe"
        className="h-16 w-auto object-contain"
      />
      <div className="flex flex-col border-l border-[var(--text)] pl-5 gap-1.5">
        <span className="text-xl font-bold text-[var(--text)] uppercase tracking-wider">{data.label}</span>
        <span className="text-xs text-white bg-[#635BFF] px-2.5 py-0.5 font-bold uppercase tracking-widest rounded shadow-sm w-fit mt-1">External Service</span>
        <div className="flex flex-col items-start gap-1.5 mt-1">
          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 text-xs px-2 py-1 font-bold rounded uppercase bg-green-500/10 text-green-500">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-green-500"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
              </span>
              HEALTHY
            </div>
            <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
              PORT: 443
            </span>
          </div>
          <button onClick={() => dispatchLogEvent('stripe-cli')} className="text-xs flex items-center justify-center gap-1.5 mt-1 bg-[var(--surface)] border border-[var(--glass-border)] px-4 py-1.5 rounded hover:text-[#635BFF] hover:border-[#635BFF] transition-all w-full">
            <FiTerminal size={14} /> LOGS
          </button>
        </div>
      </div>
    </div>
    <Handle type="source" position={Position.Left} className="w-2 h-2 !bg-[#635BFF] border-none" />
  </div>
);

const LbNode = ({ data }: any) => (
  <div className="relative w-[320px] h-[340px] flex flex-col items-center justify-center group drop-shadow-[0_4px_10px_rgba(0,0,0,0.1)] transition-transform hover:scale-105">
    <Handle type="target" position={Position.Top} className="w-2 h-2 !bg-[var(--text)] border-none top-0 z-10 opacity-0" />
    <Handle id="top-right" type="target" position={Position.Right} style={{ top: '25%', right: 0, transform: 'translate(50%, -50%)' }} className="w-2 h-2 !bg-[var(--text)] border-none z-10 opacity-0" />

    {/* Hexagon Border Layer */}
    <div className="absolute inset-0 bg-[var(--text)]" style={{ clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}></div>
    {/* Hexagon Inner Layer */}
    <div className="absolute inset-[2px] bg-[var(--surface-solid)]" style={{ clipPath: 'polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)' }}></div>

    <div className="relative z-10 flex flex-col items-center justify-center gap-3">
      <div className="relative flex justify-center mb-1">
        <img
          src="https://images.icon-icons.com/2699/PNG/512/nginx_logo_icon_169915.png"
          alt="NGINX"
          className="h-20 w-auto object-contain drop-shadow-md"
        />
      </div>
      <span className="text-xl font-bold text-[var(--text)] uppercase tracking-wider">{data.label}</span>
      <div className="flex flex-col items-center gap-1.5">
        <span className="text-xs text-white bg-[#009639] px-2.5 py-0.5 font-bold uppercase tracking-widest rounded shadow-sm">Load Balancer</span>
        {data.port && (
          <div className="flex flex-col items-center gap-1.5 mt-2">
            <div className="flex items-center gap-2.5">
              <div className={`flex items-center gap-2 text-xs px-2 py-1 font-bold rounded uppercase ${data.status === 'DOWN' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                <span className="relative flex h-2.5 w-2.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                </span>
                {data.status || 'HEALTHY'}
              </div>
              <a href={`http://localhost:${data.port}`} target="_blank" rel="noopener noreferrer" className="text-xs text-[var(--text-muted)] hover:text-[var(--primary)] flex items-center gap-1 transition-colors">
                Port: {data.port} <LiaExternalLinkAltSolid size={14} />
              </a>
            </div>
            <button onClick={() => dispatchLogEvent('nginx-lb')} className="text-xs flex items-center justify-center gap-1.5 mt-1 bg-[var(--surface)] border border-[var(--glass-border)] px-4 py-1.5 rounded hover:text-[var(--primary)] hover:border-[var(--primary)] transition-all w-full">
              <FiTerminal size={14} /> LOGS
            </button>
          </div>
        )}
      </div>
    </div>

    <Handle type="source" position={Position.Bottom} className="w-2 h-2 !bg-[var(--text)] border-none bottom-0 z-10 opacity-0" />
  </div>
);

const AppNode = ({ data }: any) => (
  <BaseNode data={data} targetPos={Position.Top} sourcePos={Position.Bottom} className={`!border-${data.status === 'DOWN' ? 'red-500' : '[var(--text)]'} border-2 transition-transform hover:scale-105`}>
    <Handle id="right" type="source" position={Position.Right} className="w-2 h-2 !bg-[var(--text)] border-none opacity-0" />
    <div className="flex flex-col items-center justify-center gap-3">
      <div className="relative flex justify-center mb-1">
        <img 
          src={SettleLogo}
          alt="Settle Node"
          className={`h-16 w-auto object-contain ${data.status === 'DOWN' ? 'grayscale opacity-50' : ''}`}
        />
      </div>
      <span className="text-xl font-bold text-[var(--text)] tracking-wider">{data.label}</span>
      <div className="flex flex-col items-center gap-1.5">
        <span className={`text-xs text-[var(--background)] px-2.5 py-0.5 font-bold uppercase tracking-widest rounded shadow-sm ${data.role === 'LEADER' ? 'bg-[var(--primary)]' : 'bg-[var(--text)]'}`}>
          {data.role || 'FOLLOWER'}
        </span>
        {data.port && (
          <div className="flex flex-col items-center gap-1.5 mt-2">
            <div className="flex items-center gap-2.5">
              <div className={`flex items-center gap-2 text-xs px-2 py-1 font-bold rounded uppercase ${data.status === 'DOWN' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                <span className="relative flex h-2.5 w-2.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                </span>
                {data.status || 'HEALTHY'}
              </div>
              <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                PORT: {data.port}
              </span>
            </div>
            <button onClick={() => dispatchLogEvent(data.label)} className="text-xs flex items-center justify-center gap-1.5 mt-1 bg-[var(--surface)] border border-[var(--glass-border)] px-4 py-1.5 rounded hover:text-[var(--primary)] hover:border-[var(--primary)] transition-all w-full">
              <FiTerminal size={14} /> LOGS
            </button>
          </div>
        )}
      </div>
    </div>
  </BaseNode>
);

const DbNode = ({ data }: any) => (
  <div className="flex flex-col items-center justify-center gap-3 relative group min-w-[200px]">
    <Handle id="top" type="target" position={Position.Top} className="w-2 h-2 !bg-[var(--primary)] border-none opacity-0" />
    <Handle id="bottom-source" type="source" position={Position.Bottom} className="w-2 h-2 !bg-[#336791] border-none opacity-0 -bottom-2" />
    <Handle id="bottom-target" type="target" position={Position.Bottom} className="w-2 h-2 !bg-[#336791] border-none opacity-0 -bottom-2" />
    <div className="relative flex items-center justify-center">
      <FiDatabase size={130} strokeWidth={0.35} className={`text-[var(--text)] transition-colors ${data.status === 'DOWN' ? 'text-red-500/50' : ''}`} />
      <img
        src="https://upload.wikimedia.org/wikipedia/commons/thumb/2/29/Postgresql_elephant.svg/1280px-Postgresql_elephant.svg.png"
        alt="PostgreSQL"
        className={`absolute w-16 h-16 object-contain mt-6 ${data.status === 'DOWN' ? 'grayscale opacity-50' : ''}`}
      />
    </div>
    <span className="text-xl font-bold text-[var(--text)] tracking-wider">{data.label}</span>
    <div className="flex flex-col items-center gap-1.5">
        <span className={`text-xs text-[var(--background)] px-2.5 py-0.5 font-bold uppercase tracking-widest rounded shadow-sm ${data.role === 'PRIMARY' ? 'bg-[#336791]' : 'bg-[var(--text-muted)]'}`}>
          {data.role || 'REPLICA'}
        </span>
        {data.port && (
          <div className="flex flex-col items-center gap-1.5 mt-2">
            <div className="flex items-center gap-2.5">
              <div className={`flex items-center gap-2 text-xs px-2 py-1 font-bold rounded uppercase ${data.status === 'DOWN' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                <span className="relative flex h-2.5 w-2.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                </span>
                {data.status || 'HEALTHY'}
              </div>
              <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                PORT: {data.port}
              </span>
            </div>
            <button onClick={() => dispatchLogEvent(data.label)} className="text-xs flex items-center justify-center gap-1.5 mt-1 bg-[var(--surface)] border border-[var(--glass-border)] px-4 py-1.5 rounded hover:text-[var(--primary)] hover:border-[var(--primary)] transition-all w-full">
              <FiTerminal size={14} /> LOGS
            </button>
          </div>
        )}
    </div>
  </div>
);

const ZkNode = ({ data }: any) => (
  <BaseNode data={data} targetPos={Position.Left} sourcePos={Position.Bottom} className="!border-[var(--text)] border-2 transition-transform hover:scale-105">
    <div className="flex flex-col items-center justify-center gap-3 group">
      <div className="relative flex justify-center mb-1">
        <img
          src="https://upload.wikimedia.org/wikipedia/commons/7/77/Apache_ZooKeeper_logo.svg"
          alt="ZooKeeper"
          className="h-28 w-auto"
        />
      </div>
      <span className="text-xl font-bold text-[var(--text)] uppercase tracking-wider">{data.label}</span>
      <div className="flex flex-col items-center gap-1.5">
        <span className="text-xs text-white bg-[#f59e0b] px-2.5 py-0.5 font-bold uppercase tracking-widest rounded shadow-sm">Coordination Service</span>
        {data.port && (
          <div className="flex flex-col items-center gap-1.5 mt-2">
            <div className="flex items-center gap-2.5">
              <div className={`flex items-center gap-2 text-xs px-2 py-1 font-bold rounded uppercase ${data.status === 'DOWN' ? 'bg-red-500/10 text-red-500' : 'bg-green-500/10 text-green-500'}`}>
                <span className="relative flex h-2.5 w-2.5">
                  <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                  <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${data.status === 'DOWN' ? 'bg-red-500' : 'bg-green-500'}`}></span>
                </span>
                {data.status || 'HEALTHY'}
              </div>
              <span className="text-xs text-[var(--text-muted)] flex items-center gap-1">
                PORT: {data.port}
              </span>
            </div>
            <button onClick={() => dispatchLogEvent('zookeeper')} className="text-xs flex items-center justify-center gap-1.5 mt-1 bg-[var(--surface)] border border-[var(--glass-border)] px-4 py-1.5 rounded hover:text-[var(--primary)] hover:border-[var(--primary)] transition-all w-full">
              <FiTerminal size={14} /> LOGS
            </button>
          </div>
        )}
      </div>
    </div>
  </BaseNode>
);

const ObsNode = ({ data }: any) => {
  const services = [
    { name: 'Prometheus', port: 9090, logo: 'https://upload.wikimedia.org/wikipedia/commons/3/38/Prometheus_software_logo.svg' },
    { name: 'Grafana', port: 3000, logo: 'https://upload.wikimedia.org/wikipedia/commons/thumb/3/3b/Grafana_icon.svg/250px-Grafana_icon.svg.png' },
    { name: 'Jaeger', port: 16686, logo: 'https://www.jaegertracing.io/img/jaeger-icon-color.png' },
    { name: 'Loki', port: 3100, logo: 'https://cdn.jsdelivr.net/gh/homarr-labs/dashboard-icons/png/loki.png' },
  ];

  return (
    <BaseNode data={data} targetPos={Position.Left} sourcePos={null} className="!border-[var(--text)] border-2 transition-transform hover:scale-105">
      <div className="flex flex-col items-center justify-center gap-5 w-[360px] group">
        <div className="flex flex-col items-center gap-2">
          <FiActivity className="text-purple-500 mb-1" size={28} />
          <span className="text-xl font-bold text-[var(--text)] uppercase tracking-wider">{data.label}</span>
          <span className="text-xs text-white bg-purple-500 px-2.5 py-0.5 font-bold uppercase tracking-widest rounded shadow-sm mt-1">Observability Stack</span>
        </div>
        <div className="grid grid-cols-2 gap-3 w-full mt-3 border-t border-[var(--glass-border)] pt-5">
          {services.map((svc) => (
            <div key={svc.name} className="flex flex-col items-center p-3 border border-[var(--glass-border)] rounded bg-[var(--surface-sunken)] gap-1.5 hover:border-purple-500/50 transition-colors">
              <img src={svc.logo} alt={svc.name} className="h-14 w-auto object-contain mb-1.5" />
              <span className="text-xs font-bold text-[var(--text)] uppercase text-center">{svc.name}</span>
              
              <div className="flex items-center gap-1.5 text-[10px] px-2 py-1 font-bold rounded uppercase bg-green-500/10 text-green-500">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 bg-green-500"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                HEALTHY
              </div>
              
              <a href={`http://localhost:${svc.port}`} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[var(--text-muted)] hover:text-purple-500 flex items-center gap-1 transition-colors mt-1">
                Port: {svc.port} <LiaExternalLinkAltSolid size={14} />
              </a>
              <button onClick={() => dispatchLogEvent(svc.name.toLowerCase())} className="text-[10px] flex items-center justify-center gap-1.5 mt-2 bg-[var(--surface)] border border-[var(--glass-border)] px-4 py-1.5 rounded hover:text-purple-500 hover:border-purple-500 transition-all w-full">
                <FiTerminal size={14} /> LOGS
              </button>
            </div>
          ))}
        </div>
      </div>
    </BaseNode>
  );
};

const nodeTypes = {
  client: ClientNode,
  external: ExternalNode,
  lb: LbNode,
  app: AppNode,
  db: DbNode,
  zk: ZkNode,
  obs: ObsNode
};

const initialNodes: Node[] = [
  { id: 'client-web', type: 'client', position: { x: 250, y: -50 }, data: { label: 'Web Clients', icon: 'web' } },
  { id: 'client-mobile', type: 'client', position: { x: 550, y: -50 }, data: { label: 'Mobile Apps', icon: 'mobile' } },

  { id: 'stripe', type: 'external', position: { x: 800, y: -50 }, data: { label: 'Stripe API Webhooks' } },
  { id: 'nginx', type: 'lb', position: { x: 400, y: 150 }, data: { label: 'NGINX' } },

  { id: 'zookeeper', type: 'zk', position: { x: 400, y: 450 }, data: { label: 'ZooKeeper' } },

  { id: 'node-1', type: 'app', position: { x: 50, y: 300 }, data: { label: 'settle-node-1' } },
  { id: 'node-2', type: 'app', position: { x: 270, y: 300 }, data: { label: 'settle-node-2' } },
  { id: 'node-3', type: 'app', position: { x: 490, y: 300 }, data: { label: 'settle-node-3' } },
  { id: 'node-4', type: 'app', position: { x: 710, y: 300 }, data: { label: 'settle-node-4' } },
  { id: 'node-5', type: 'app', position: { x: 930, y: 300 }, data: { label: 'settle-node-5' } },

  { id: 'db-1', type: 'db', position: { x: 490, y: 550 }, data: { label: 'postgres-1' } },
  { id: 'db-2', type: 'db', position: { x: 50, y: 780 }, data: { label: 'postgres-2' } },
  { id: 'db-3', type: 'db', position: { x: 340, y: 780 }, data: { label: 'postgres-3' } },
  { id: 'db-4', type: 'db', position: { x: 640, y: 780 }, data: { label: 'postgres-4' } },
  { id: 'db-5', type: 'db', position: { x: 930, y: 780 }, data: { label: 'postgres-5' } },

  { id: 'obs', type: 'obs', position: { x: 1200, y: 300 }, data: { label: 'Telemetry & Logs' } },
];

const labelProps = {
  labelStyle: { fill: 'var(--text)', fontWeight: 600, fontSize: 10 },
  labelBgStyle: { fill: 'var(--surface-solid)', stroke: 'var(--text-muted)', strokeWidth: 1 },
  labelBgPadding: [6, 4] as [number, number],
  labelBgBorderRadius: 4
};

const initialEdges: Edge[] = [
  { id: 'e-web-nginx', source: 'client-web', target: 'nginx', animated: true, label: 'HTTPS', ...labelProps, style: { stroke: 'var(--text)', strokeWidth: 1.5 } },
  { id: 'e-mobile-nginx', source: 'client-mobile', target: 'nginx', animated: true, label: 'HTTPS', ...labelProps, style: { stroke: 'var(--text)', strokeWidth: 1.5 } },
  { id: 'e-stripe-nginx', source: 'stripe', target: 'nginx', targetHandle: 'top-right', animated: true, label: 'Webhook / HTTPS', ...labelProps, style: { stroke: '#635BFF', strokeWidth: 2 } },

  { id: 'e-nginx-n1', source: 'nginx', target: 'node-1', animated: true, label: 'HTTP/2', ...labelProps, style: { stroke: 'var(--primary)', strokeWidth: 1.5, opacity: 0.6 } },
  { id: 'e-nginx-n2', source: 'nginx', target: 'node-2', animated: true, label: 'HTTP/2', ...labelProps, style: { stroke: 'var(--primary)', strokeWidth: 1.5, opacity: 0.6 } },
  { id: 'e-nginx-n3', source: 'nginx', target: 'node-3', animated: true, label: 'HTTP/2', ...labelProps, style: { stroke: 'var(--primary)', strokeWidth: 1.5, opacity: 0.6 } },
  { id: 'e-nginx-n4', source: 'nginx', target: 'node-4', animated: true, label: 'HTTP/2', ...labelProps, style: { stroke: 'var(--primary)', strokeWidth: 1.5, opacity: 0.6 } },
  { id: 'e-nginx-n5', source: 'nginx', target: 'node-5', animated: true, label: 'HTTP/2', ...labelProps, style: { stroke: 'var(--primary)', strokeWidth: 1.5, opacity: 0.6 } },

  { id: 'e-n1-zk', source: 'node-1', sourceHandle: 'right', target: 'zookeeper', animated: true, label: 'TCP / 2181', ...labelProps, style: { stroke: '#f59e0b', strokeWidth: 1, strokeDasharray: '5 5' } },
  { id: 'e-n2-zk', source: 'node-2', sourceHandle: 'right', target: 'zookeeper', animated: true, label: 'TCP / 2181', ...labelProps, style: { stroke: '#f59e0b', strokeWidth: 1, strokeDasharray: '5 5' } },
  { id: 'e-n3-zk', source: 'node-3', sourceHandle: 'right', target: 'zookeeper', animated: true, label: 'TCP / 2181', ...labelProps, style: { stroke: '#f59e0b', strokeWidth: 1, strokeDasharray: '5 5' } },
  { id: 'e-n4-zk', source: 'node-4', sourceHandle: 'right', target: 'zookeeper', animated: true, label: 'TCP / 2181', ...labelProps, style: { stroke: '#f59e0b', strokeWidth: 1, strokeDasharray: '5 5' } },
  { id: 'e-n5-zk', source: 'node-5', sourceHandle: 'right', target: 'zookeeper', animated: true, label: 'TCP / 2181', ...labelProps, style: { stroke: '#f59e0b', strokeWidth: 1, strokeDasharray: '5 5' } },

  { id: 'e-n1-db', source: 'node-1', sourceHandle: 'bottom', target: 'db-1', animated: true, label: 'TCP / 5432', ...labelProps, style: { stroke: '#336791', strokeWidth: 2 } },
  { id: 'e-n2-db', source: 'node-2', sourceHandle: 'bottom', target: 'db-2', animated: true, label: 'TCP / 5432', ...labelProps, style: { stroke: '#336791', strokeWidth: 2 } },
  { id: 'e-n3-db', source: 'node-3', sourceHandle: 'bottom', target: 'db-3', animated: true, label: 'TCP / 5432', ...labelProps, style: { stroke: '#336791', strokeWidth: 2 } },
  { id: 'e-n4-db', source: 'node-4', sourceHandle: 'bottom', target: 'db-4', animated: true, label: 'TCP / 5432', ...labelProps, style: { stroke: '#336791', strokeWidth: 2 } },
  { id: 'e-n5-db', source: 'node-5', sourceHandle: 'bottom', target: 'db-5', animated: true, label: 'TCP / 5432', ...labelProps, style: { stroke: '#336791', strokeWidth: 2 } },

  { id: 'e-repl-1', source: 'db-1', sourceHandle: 'bottom-source', target: 'db-2', targetHandle: 'bottom-target', animated: true, label: 'WAL Replication', ...labelProps, style: { stroke: '#336791', strokeWidth: 2, strokeDasharray: '5 5' } },
  { id: 'e-repl-2', source: 'db-1', sourceHandle: 'bottom-source', target: 'db-3', targetHandle: 'bottom-target', animated: true, label: 'WAL Replication', ...labelProps, style: { stroke: '#336791', strokeWidth: 2, strokeDasharray: '5 5' } },
  { id: 'e-repl-3', source: 'db-1', sourceHandle: 'bottom-source', target: 'db-4', targetHandle: 'bottom-target', animated: true, label: 'WAL Replication', ...labelProps, style: { stroke: '#336791', strokeWidth: 2, strokeDasharray: '5 5' } },
  { id: 'e-repl-4', source: 'db-1', sourceHandle: 'bottom-source', target: 'db-5', targetHandle: 'bottom-target', animated: true, label: 'WAL Replication', ...labelProps, style: { stroke: '#336791', strokeWidth: 2, strokeDasharray: '5 5' } },

  { id: 'e-n5-obs', source: 'node-5', target: 'obs', animated: true, label: 'UDP / TCP', ...labelProps, style: { stroke: '#a855f7', strokeWidth: 1, strokeDasharray: '4 4' } },
  { id: 'e-n4-obs', source: 'node-4', target: 'obs', animated: true, label: 'UDP / TCP', ...labelProps, style: { stroke: '#a855f7', strokeWidth: 1, strokeDasharray: '4 4' } },
  { id: 'e-n3-obs', source: 'node-3', target: 'obs', animated: true, label: 'UDP / TCP', ...labelProps, style: { stroke: '#a855f7', strokeWidth: 1, strokeDasharray: '4 4' } },
  { id: 'e-n2-obs', source: 'node-2', target: 'obs', animated: true, label: 'UDP / TCP', ...labelProps, style: { stroke: '#a855f7', strokeWidth: 1, strokeDasharray: '4 4' } },
  { id: 'e-n1-obs', source: 'node-1', target: 'obs', animated: true, label: 'UDP / TCP', ...labelProps, style: { stroke: '#a855f7', strokeWidth: 1, strokeDasharray: '4 4' } }
];

import { useTheme } from '../hooks/useTheme';

const LOCAL_STORAGE_KEY = 'settle_architecture_nodes';

const loadSavedNodes = (): Node[] => {
  const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
  if (saved) {
    try {
      const savedNodes = JSON.parse(saved);
      return initialNodes.map(node => {
        const savedNode = savedNodes.find((n: any) => n.id === node.id);
        if (savedNode && savedNode.position) {
          return { ...node, position: savedNode.position };
        }
        return node;
      });
    } catch (e) {
      console.error('Failed to parse saved nodes', e);
    }
  }
  return initialNodes;
};

const LogPanel = ({ tabs, activeTab, onTabClick, onClose, onCloseTab }: any) => {
  const [logs, setLogs] = useState<string[]>([]);
  const logsEndRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (!activeTab) return;
    let interval = setInterval(async () => {
      try {
        const res = await fetch(`/api/dev/logs/${activeTab}`);
        if (res.ok) {
           const data = await res.json();
           setLogs(data.logs);
        }
      } catch (e) {}
    }, 2000);
    
    // Initial fetch
    fetch(`/api/dev/logs/${activeTab}`).then(r => r.json()).then(d => setLogs(d.logs || [])).catch(() => {});
    
    return () => clearInterval(interval);
  }, [activeTab]);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <motion.div 
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', damping: 25, stiffness: 200 }}
      className="absolute top-0 right-0 w-[600px] max-w-[90vw] h-full bg-[var(--surface-solid)] border-l border-[var(--glass-border)] flex flex-col z-50"
    >
       <div className="flex flex-col border-b border-[var(--glass-border)] bg-[var(--surface)]">
         <div className="flex justify-between items-center p-4 border-b border-[var(--glass-border)]">
           <span className="font-space font-bold flex items-center gap-2"><FiTerminal className="text-[var(--primary)]"/> Terminal Logs</span>
           <button onClick={onClose} className="hover:text-[var(--primary)] transition-colors"><FiX size={20}/></button>
         </div>
         <div className="flex overflow-x-auto p-2 gap-2 min-h-[44px]">
           {tabs.map((tab: string) => (
              <div key={tab} className={`flex items-center gap-2 px-3 py-1.5 border border-[var(--glass-border)] cursor-pointer text-xs font-google-code rounded-sm transition-colors whitespace-nowrap ${activeTab === tab ? 'bg-[var(--text)] text-[var(--surface-solid)] border-[var(--text)]' : 'hover:bg-[var(--surface-sunken)]'}`} onClick={() => onTabClick(tab)}>
                {tab}
                <button onClick={(e) => { e.stopPropagation(); onCloseTab(tab); }} className={`ml-1 opacity-70 hover:opacity-100 ${activeTab === tab ? 'hover:text-red-400' : 'hover:text-red-500'}`}><FiX/></button>
              </div>
           ))}
           {tabs.length === 0 && <span className="text-xs text-[var(--text-muted)] italic py-1.5 px-2">No active terminals</span>}
         </div>
       </div>
       <div className="flex-1 bg-[#1e1e1e] text-[#d4d4d4] font-google-code text-[11px] md:text-xs p-4 overflow-y-auto leading-relaxed">
         {logs.map((log, i) => {
           let color = 'text-[#d4d4d4]';
           if (log.toLowerCase().includes('error')) color = 'text-red-400';
           else if (log.toLowerCase().includes('warn')) color = 'text-yellow-400';
           else if (log.includes('INFO') || log.includes('info')) color = 'text-blue-300';
           else if (log.includes('DEBUG')) color = 'text-gray-500';
           return <div key={i} className={`whitespace-pre-wrap break-all mb-1 ${color}`}>{log}</div>;
         })}
         {logs.length === 0 && <div className="text-gray-500 italic">Waiting for logs...</div>}
         <div ref={logsEndRef} />
       </div>
    </motion.div>
  )
}

const FlowInit = () => {
  const store = useStoreApi();
  useEffect(() => {
    store.setState({ 
      nodesDraggable: false, 
      nodesConnectable: false, 
      elementsSelectable: false 
    });
  }, [store]);
  return null;
};

export default function Architecture() {
  const { theme } = useTheme();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>(loadSavedNodes());
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>(initialEdges);
  
  const [logTabs, setLogTabs] = useState<string[]>([]);
  const [activeLogTab, setActiveLogTab] = useState<string | null>(null);
  const [isLogPanelOpen, setIsLogPanelOpen] = useState(false);

  useEffect(() => {
    const handleOpenLogs = (e: any) => {
      const nodeId = e.detail.nodeId;
      if (!logTabs.includes(nodeId)) {
        setLogTabs(prev => [...prev, nodeId]);
      }
      setActiveLogTab(nodeId);
      setIsLogPanelOpen(true);
    };
    window.addEventListener('open-node-logs', handleOpenLogs);
    return () => window.removeEventListener('open-node-logs', handleOpenLogs);
  }, [logTabs]);

  const handleCloseTab = (tab: string) => {
    const newTabs = logTabs.filter(t => t !== tab);
    setLogTabs(newTabs);
    if (activeLogTab === tab) {
      setActiveLogTab(newTabs.length > 0 ? newTabs[newTabs.length - 1] : null);
    }
  };

  useEffect(() => {
    const nodePositions = nodes.map(n => ({ id: n.id, position: n.position }));
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(nodePositions));
  }, [nodes]);

  useEffect(() => {
    let interval: any;

    const fetchTopologyData = async () => {
      try {
        const [clusterRes, dbRes] = await Promise.all([
          fetch('/api/v1/health/cluster').catch(() => null),
          fetch('/api/v1/database/metrics').catch(() => null),
        ]);

        let leaderId = null;
        let activePeers: string[] = [];
        if (clusterRes && clusterRes.ok) {
          const cdata = await clusterRes.json();
          leaderId = cdata.leader_id;
          activePeers = cdata.cluster_members || [];
        }

        let dbMetrics: any[] = [];
        if (dbRes && dbRes.ok) {
          dbMetrics = await dbRes.json();
        }

        setNodes((nds) =>
          nds.map((n) => {
            if (n.type === 'app') {
              const isActive = activePeers.includes(n.id);
              const isLeader = leaderId === n.id;
              return {
                ...n,
                data: {
                  ...n.data,
                  status: isActive ? 'HEALTHY' : 'DOWN',
                  role: isLeader ? 'LEADER' : 'FOLLOWER',
                  port: 8000 + parseInt(n.id.replace('node-', '')),
                },
              };
            }
            if (n.type === 'db') {
              const dbInfo = dbMetrics.find(d => d.id === n.id.replace('db-', 'postgres-'));
              return {
                ...n,
                data: {
                  ...n.data,
                  status: dbInfo ? dbInfo.status : 'DOWN',
                  role: dbInfo ? dbInfo.role : 'REPLICA',
                  port: 5432,
                },
              };
            }
            if (n.type === 'lb') {
              return { ...n, data: { ...n.data, port: 8000, status: 'HEALTHY' } };
            }
            if (n.type === 'zk') {
              return { ...n, data: { ...n.data, port: 2181, status: 'HEALTHY' } };
            }
            return n;
          })
        );
      } catch (e) {
        console.warn('Failed to fetch topology data', e);
      }
    };

    fetchTopologyData();
    interval = setInterval(fetchTopologyData, 1000);
    return () => clearInterval(interval);
  }, [setNodes]);

  const onConnect = useCallback((params: any) => setEdges((eds) => addEdge(params, eds)), [setEdges]);

  return (
    <div className="h-full w-full flex flex-col overflow-hidden relative">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex items-center gap-3 mb-8"
      >
        <div className="text-[var(--primary)]">
          <FiMap size={48} />
        </div>
        <div>
          <h1 className="text-3xl font-light text-[var(--text)] tracking-tight">System Architecture</h1>
          <p className="text-[var(--text-muted)] text-sm font-medium mt-1 uppercase tracking-widest">Interactive Network Topology</p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.1 }}
        className="flex-1 overflow-hidden relative"
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={nodeTypes}
          fitView
          fitViewOptions={{ padding: 0.2 }}
          minZoom={0.2}
          className="bg-transparent"
          colorMode={theme}
        >
          <FlowInit />
          <Controls className="!bg-[var(--surface-solid)] !border-[var(--glass-border)] !rounded-none shadow-sm [&>button]:!bg-transparent [&>button]:!border-b-[var(--glass-border)] [&>button]:!text-[var(--text)] hover:[&>button]:!text-[var(--primary)]" />
        </ReactFlow>
      </motion.div>

      <AnimatePresence>
        {isLogPanelOpen && (
          <LogPanel 
            tabs={logTabs} 
            activeTab={activeLogTab} 
            onTabClick={setActiveLogTab} 
            onClose={() => setIsLogPanelOpen(false)} 
            onCloseTab={handleCloseTab} 
          />
        )}
      </AnimatePresence>
    </div>
  );
}
