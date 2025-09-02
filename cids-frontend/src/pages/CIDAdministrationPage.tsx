import React, { useEffect, useMemo, useRef, useState } from 'react';
import './TokenAdministrationPage.css';
import adminService from '../services/adminService';
import LogTable from '../components/LogTable';

const CIDAdministrationPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'logging' | 'logs' | 'maintenance'>('logging');

  // Logging settings
  const [config, setConfig] = useState<any | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Logs viewer
  const [logKind, setLogKind] = useState<'app' | 'audit' | 'token-activity'>('app');
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [q, setQ] = useState('');
  const [levelFilter, setLevelFilter] = useState<string>('');
  const tailAbortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (activeTab === 'logging') {
      (async () => {
        try {
          const cfg = await adminService.getLoggingConfig();
          setConfig(cfg);
        } catch (e:any) {
          // ignore for now; show minimal error
          console.error(e);
        }
      })();
    }
  }, [activeTab]);

  const appColumns = useMemo(() => ([
    { key: 'timestamp', label: 'Time' },
    { key: 'level', label: 'Level' },
    { key: 'logger', label: 'Logger' },
    { key: 'http.request.method', label: 'Method' },
    { key: 'url.path', label: 'Path' },
    { key: 'http.response.status_code', label: 'Status' },
    { key: 'user.email', label: 'User' },
    { key: 'source.ip', label: 'IP' },
    { key: 'duration.ms', label: 'ms' },
    { key: 'message', label: 'Message' },
  ]), []);

  const auditColumns = useMemo(() => ([
    { key: 'timestamp', label: 'Time' },
    { key: 'action', label: 'Action' },
    { key: 'user.email', label: 'User' },
    { key: 'resource.type', label: 'Res Type' },
    { key: 'resource.id', label: 'Res ID' },
    { key: 'details', label: 'Details' },
  ]), []);

  const tokenColumns = useMemo(() => ([
    { key: 'timestamp', label: 'Time' },
    { key: 'action', label: 'Action' },
    { key: 'token_id', label: 'Token ID' },
    { key: 'performed_by.email', label: 'By' },
    { key: 'details', label: 'Details' },
  ]), []);

  const columns = logKind === 'app' ? appColumns : logKind === 'audit' ? auditColumns : tokenColumns;

  const fetchLogs = async () => {
    try {
      setLoading(true); setError(null);
      if (logKind === 'app') {
        const res = await adminService.getAppLogs({ limit: 200, level: levelFilter });
        setItems(res.items);
      } else if (logKind === 'audit') {
        const res = await adminService.getAuditLogs({ limit: 200 });
        setItems(res.items);
      } else {
        const res = await adminService.getTokenActivityLogs({ limit: 200 });
        setItems(res.items);
      }
    } catch (e:any) {
      setError(e.message || 'Failed to load logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'logs') {
      fetchLogs();
    }
    return () => {
      // cleanup tail on tab change
      if (tailAbortRef.current) {
        tailAbortRef.current.abort();
        tailAbortRef.current = null;
      }
    };
  }, [activeTab, logKind]);

  const startLiveTail = async () => {
    // Abort any existing tail
    if (tailAbortRef.current) {
      tailAbortRef.current.abort();
      tailAbortRef.current = null;
    }
    const controller = new AbortController();
    tailAbortRef.current = controller;

    const origin = window.location.origin;
    const path = logKind === 'app' ? '/auth/admin/logs/app/stream' : logKind === 'audit' ? '/auth/admin/logs/audit/stream' : '/auth/admin/logs/token-activity/stream';
    const token = localStorage.getItem('access_token');
    try {
      const resp = await fetch(origin + path, {
        method: 'GET',
        headers: token ? { Authorization: `Bearer ${token}` } : undefined,
        signal: controller.signal,
      });
      if (!resp.ok || !resp.body) throw new Error('Stream connection failed');

      const reader = resp.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        let idx;
        while ((idx = buffer.indexOf('\n\n')) !== -1) {
          const eventChunk = buffer.slice(0, idx);
          buffer = buffer.slice(idx + 2);
          const dataLine = eventChunk.split('\n').find(line => line.startsWith('data:'));
          if (dataLine) {
            const payload = dataLine.slice(5).trim();
            try {
              const obj = JSON.parse(payload);
              setItems(prev => [obj, ...prev].slice(0, 500));
            } catch {}
          }
        }
      }
    } catch (e) {
      // silently stop
    } finally {
      if (tailAbortRef.current === controller) tailAbortRef.current = null;
    }
  };

  const stopLiveTail = () => {
    if (tailAbortRef.current) {
      tailAbortRef.current.abort();
      tailAbortRef.current = null;
    }
  };

  const handleDownload = async (format: 'ndjson' | 'csv') => {
    try {
      const blob: any = await adminService.exportLogs(logKind, format, 50000);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${logKind}_logs.${format === 'csv' ? 'csv' : 'ndjson'}`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e:any) {
      alert(e.message || 'Download failed');
    }
  };

  const redacted = useMemo(() => {
    const ql = q.toLowerCase();
    return items.filter(it => {
      if (!q) return true;
      return JSON.stringify(it).toLowerCase().includes(ql);
    });
  }, [items, q]);

  const [patch, setPatch] = useState<any>({});
  const applyConfig = async () => {
    try {
      setSaving(true); setSaveError(null);
      const updated = await adminService.updateLoggingConfig(patch);
      setConfig(updated);
      setPatch({});
      alert('Logging config updated');
    } catch (e:any) {
      setSaveError(e.message || 'Failed to update');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="token-admin-page">
      <div className="page-header">
        <h1>CID Administration</h1>
        <p className="page-subtitle">Configure logging, view logs, and perform maintenance</p>
      </div>

      <div className="tab-navigation">
        <button className={`tab-button ${activeTab === 'logging' ? 'active' : ''}`} onClick={() => setActiveTab('logging')}>Logging Settings</button>
        <button className={`tab-button ${activeTab === 'logs' ? 'active' : ''}`} onClick={() => setActiveTab('logs')}>Logs Viewer</button>
        <button className={`tab-button ${activeTab === 'maintenance' ? 'active' : ''}`} onClick={() => setActiveTab('maintenance')}>Maintenance</button>
      </div>

      <div className="tab-content">
        {activeTab === 'logging' && (
          <div>
            <h3>Logging Settings</h3>
            {!config && <div className="loading">Loading current config...</div>}
            {config && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
                <div>
                  <label>App Log Level</label>
                  <select value={patch.app?.level ?? config.app?.level ?? 'INFO'} onChange={e => setPatch((p:any)=>({ ...p, app: { ...(p.app||{}), level: e.target.value } }))}>
                    <option>DEBUG</option>
                    <option>INFO</option>
                    <option>WARNING</option>
                    <option>ERROR</option>
                  </select>
                </div>
                <div>
                  <label>Access Logs Enabled</label>
                  <input type="checkbox" checked={patch.access?.enabled ?? config.access?.enabled ?? true} onChange={e => setPatch((p:any)=>({ ...p, access: { ...(p.access||{}), enabled: e.target.checked } }))} />
                </div>
                <div>
                  <label>JSON Format</label>
                  <input type="checkbox" checked={patch.app?.json ?? config.app?.json ?? true} onChange={e => setPatch((p:any)=>({ ...p, app: { ...(p.app||{}), json: e.target.checked } }))} />
                </div>
                <div>
                  <label>Stdout Enabled</label>
                  <input type="checkbox" checked={patch.app?.stdout ?? config.app?.stdout ?? true} onChange={e => setPatch((p:any)=>({ ...p, app: { ...(p.app||{}), stdout: e.target.checked } }))} />
                </div>
                <div style={{ gridColumn: '1 / -1' }}>
                  <button className="button" onClick={applyConfig} disabled={saving}>Save</button>
                  {saveError && <span className="error-message" style={{ marginLeft: 8 }}>{saveError}</span>}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'logs' && (
          <div>
            <div className="logs-controls" style={{ display: 'flex', gap: 8, marginBottom: 8, alignItems:'center', flexWrap: 'wrap' }}>
              <select value={logKind} onChange={e=>setLogKind(e.target.value as any)}>
                <option value="app">App</option>
                <option value="audit">Audit</option>
                <option value="token-activity">Token Activity</option>
              </select>
              {logKind === 'app' && (
                <>
                  <select onChange={e=>fetchLogs()} style={{ minWidth: 100 }}>
                    <option value="">All Levels</option>
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </>
              )}
              <input className="filter-input" placeholder="Filter text..." value={q} onChange={e=>setQ(e.target.value)} />
              <button className="button" onClick={fetchLogs} disabled={loading}>Refresh</button>
              <button className="button" onClick={()=>handleDownload('ndjson')}>Download NDJSON</button>
              <button className="button" onClick={()=>handleDownload('csv')}>Download CSV</button>
              <button className="button" onClick={startLiveTail} disabled={!!tailAbortRef.current}>Live Tail</button>
              <button className="button" onClick={stopLiveTail} disabled={!tailAbortRef.current}>Stop Tail</button>
            </div>
            {loading && <div className="loading">Loading logs...</div>}
            {error && <div className="error-message">{error}</div>}
            {!loading && !error && <LogTable items={redacted} columns={columns as any} emptyText="No log items" />}
          </div>
        )}

        {activeTab === 'maintenance' && (
          <div className="coming-soon">
            <h3>Maintenance</h3>
            <p>Retention cleanup, manual rotation checks and more.</p>
            <button className="button" onClick={async()=>{
              try{
                await adminService.manualRotationCheck();
                alert('Rotation check triggered');
              }catch(e:any){
                alert(e.message||'Failed to run rotation check');
              }
            }}>Run Rotation Check</button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CIDAdministrationPage;

