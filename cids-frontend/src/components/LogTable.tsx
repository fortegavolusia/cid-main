import React from 'react';

interface LogTableProps {
  items: any[];
  columns?: { key: string; label: string }[];
  emptyText?: string;
}

const DefaultColumns: { key: string; label: string }[] = [
  { key: 'timestamp', label: 'Time' },
  { key: 'level', label: 'Level' },
  { key: 'logger', label: 'Logger' },
  { key: 'message', label: 'Message' },
];

function getByPath(obj: any, path: string): any {
  if (!obj) return undefined;
  // Try nested traversal for dotted paths
  if (path.includes('.')) {
    const nested = path.split('.').reduce((acc: any, part: string) => (acc ? acc[part] : undefined), obj);
    if (nested !== undefined) return nested;
    // Fallback: some logs are flat keys with dots (e.g., 'http.request.method')
    if (Object.prototype.hasOwnProperty.call(obj, path)) return obj[path];
    return undefined;
  }
  return obj[path];
}

const LogTable: React.FC<LogTableProps> = ({ items, columns = DefaultColumns, emptyText = 'No items' }) => {
  if (!items.length) return <p>{emptyText}</p>;
  return (
    <div style={{ overflowX: 'auto' }}>
      <table className="token-table">
        <thead>
          <tr>
            {columns.map(c => (
              <th key={c.key}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it, idx) => (
            <tr key={idx}>
              {columns.map(c => {
                const val = getByPath(it, c.key);
                const display = typeof val === 'object' && val !== null ? JSON.stringify(val) : (val ?? '—');
                return (
                  <td key={c.key} style={{ fontFamily: c.key.toLowerCase().includes('id') ? 'monospace' as const : undefined, fontSize: '12px' }}>
                    {String(display)}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default LogTable;

