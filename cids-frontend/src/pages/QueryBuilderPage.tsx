import { useMemo, useState } from 'react';
import styled from 'styled-components';
import 'antd/dist/reset.css';
import '@react-awesome-query-builder/ui/css/styles.css';
import {
  Query,
  Builder,
  Utils as QbUtils,
} from '@react-awesome-query-builder/ui';
import { AntdConfig } from '@react-awesome-query-builder/antd';
import { savePolicy, loadPolicy, listPolicies, deletePolicy } from '../services/localPolicyService';

const Container = styled.div`
  background-color: white;
  border-radius: 6px;
  box-shadow: var(--card-shadow);
  padding: 24px;
`;

const Title = styled.h1`
  color: rgba(0, 0, 0, 0.85);
  margin: 0 0 24px 0;
  font-size: 24px;
  font-weight: 500;
`;

const ControlsRow = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
`;

const Input = styled.input`
  padding: 6px 10px;
  border: 1px solid var(--border-color);
  border-radius: var(--border-radius);
  font-size: 14px;
`;

const Button = styled.button`
  background-color: var(--primary-color);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: var(--border-radius);
  cursor: pointer;
  text-decoration: none;
  display: inline-block;
  transition: all 0.3s ease;
  font-size: 14px;
  line-height: 1.5715;
  font-weight: 400;
  box-shadow: 0 2px 0 rgba(0, 0, 0, 0.015);
`;

const DangerButton = styled(Button)`
  background-color: var(--error-color);
`;

const Section = styled.div`
  background-color: white;
  border-radius: var(--border-radius);
  padding: 0;
  margin: 24px 0;
  border: 1px solid var(--border-color);
  box-shadow: var(--card-shadow);
`;

const SectionHeader = styled.div`
  padding: 16px 24px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  user-select: none;
  transition: all 0.3s ease;
  border-bottom: 1px solid var(--border-color);
`;

const SectionContent = styled.div`
  padding: 24px;
`;

const Output = styled.pre`
  padding: 16px;
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  background: #fafafa;
  overflow: auto;
`;

const QueryBuilderPage: React.FC = () => {
  const fields = useMemo(() => ({
    name: { label: 'Name', type: 'text' },
    email: { label: 'Email', type: 'text' },
    department: {
      label: 'Department',
      type: 'select',
      fieldSettings: {
        listValues: [
          { value: 'IT', title: 'IT' },
          { value: 'Finance', title: 'Finance' },
          { value: 'HR', title: 'HR' },
        ],
      },
    },
    age: { label: 'Age', type: 'number' },
  }), []);

  const qbConfig = useMemo(() => ({
    ...AntdConfig,
    fields,
  }), [fields]);

  const [clientId, setClientId] = useState('demo-app');
  const [role, setRole] = useState('admin');
  const [tree, setTree] = useState(QbUtils.loadTree({ id: QbUtils.uuid(), type: 'group' }));
  const [savedOpen, setSavedOpen] = useState(false);

  const jsonTree = useMemo(() => QbUtils.getTree(tree), [tree]);

  return (
    <Container>
      <Title>Query Builder</Title>

      <ControlsRow>
        <Input placeholder="Client ID" value={clientId} onChange={(e: any) => setClientId(e.target.value)} />
        <Input placeholder="Role" value={role} onChange={(e: any) => setRole(e.target.value)} />
        <Button onClick={() => setTree(QbUtils.loadTree({ id: QbUtils.uuid(), type: 'group' }))}>New</Button>
        <Button onClick={() => {
          const saved = loadPolicy(clientId, role);
          if (saved?.tree) setTree(saved.tree as any);
        }}>Load</Button>
        <Button onClick={() => savePolicy(clientId, role, tree)}>Save</Button>
        <Button onClick={() => {
          const data = JSON.stringify({ clientId, role, tree: QbUtils.getTree(tree) }, null, 2);
          const blob = new Blob([data], { type: 'application/json' });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = `${clientId}_${role}_policy.json`;
          a.click();
          URL.revokeObjectURL(url);
        }}>Export</Button>
        <Button as="label">
          Import
          <input type="file" accept="application/json" style={{ display: 'none' }} onChange={(e: any) => {
            const file = e.target.files?.[0];
            if (!file) return;
            const reader = new FileReader();
            reader.onload = () => {
              try {
                const parsed = JSON.parse(String(reader.result));
                if (parsed.clientId) setClientId(parsed.clientId);
                if (parsed.role) setRole(parsed.role);
                if (parsed.tree) setTree(QbUtils.loadTree(parsed.tree));
              } catch (err) {
                console.error('Failed to import policy JSON', err);
              }
            };
            reader.readAsText(file);
          }} />
        </Button>
        <DangerButton onClick={() => setTree(QbUtils.loadTree({ id: QbUtils.uuid(), type: 'group' }))}>Reset</DangerButton>
      </ControlsRow>

      <Query
        {...(qbConfig as any)}
        value={tree as any}
        onChange={(immutableTree: any) => setTree(immutableTree)}
        renderBuilder={(props: any) => <Builder {...props} />}
      />

      <Section>
        <SectionHeader onClick={() => setSavedOpen(!savedOpen)}>
          <h2 style={{ margin: 0 }}>Saved Policies</h2>
          <span style={{ transform: savedOpen ? 'rotate(180deg)' : 'rotate(0deg)', transition: 'transform 0.3s ease', color: 'var(--text-secondary)' }}>▼</span>
        </SectionHeader>
        {savedOpen && (
          <SectionContent>
            {listPolicies().length === 0 ? (
              <p style={{ color: 'var(--text-secondary)', margin: 0 }}>No saved policies yet.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr>
                    <th style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>Client ID</th>
                    <th style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>Role</th>
                    <th style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>Updated</th>
                    <th style={{ textAlign: 'left', padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {listPolicies().map((p, idx) => (
                    <tr key={`${p.clientId}:${p.role}:${idx}`}>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>{p.clientId}</td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>{p.role}</td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>{new Date(p.updatedAt).toLocaleString()}</td>
                      <td style={{ padding: '8px 12px', borderBottom: '1px solid var(--border-color)' }}>
                        <Button onClick={() => { setClientId(p.clientId); setRole(p.role); setTree(p.tree as any); }} style={{ marginRight: 8 }}>Load</Button>
                        <DangerButton onClick={() => { deletePolicy(p.clientId, p.role); }}>Delete</DangerButton>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </SectionContent>
        )}
      </Section>

      <h3>JSON</h3>
      <Output>{JSON.stringify(jsonTree, null, 2)}</Output>
    </Container>
  );
};

export default QueryBuilderPage;

