export type SavedPolicyEntry = {
  clientId: string;
  role: string;
  updatedAt: string;
  tree: unknown;
};

const STORAGE_KEY = 'cids:policies';

type StorageShape = Record<string, Record<string, { updatedAt: string; tree: unknown }>>;

function readStore(): StorageShape {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return {};
    return JSON.parse(raw) as StorageShape;
  } catch {
    return {};
  }
}

function writeStore(store: StorageShape) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
}

export function savePolicy(clientId: string, role: string, tree: unknown) {
  const store = readStore();
  store[clientId] = store[clientId] || {};
  store[clientId][role] = { updatedAt: new Date().toISOString(), tree };
  writeStore(store);
}

export function loadPolicy(clientId: string, role: string): SavedPolicyEntry | null {
  const store = readStore();
  const entry = store[clientId]?.[role];
  if (!entry) return null;
  return { clientId, role, ...entry };
}

export function deletePolicy(clientId: string, role: string) {
  const store = readStore();
  if (store[clientId]) {
    delete store[clientId][role];
    if (Object.keys(store[clientId]).length === 0) {
      delete store[clientId];
    }
    writeStore(store);
  }
}

export function listPolicies(): SavedPolicyEntry[] {
  const store = readStore();
  const result: SavedPolicyEntry[] = [];
  for (const clientId of Object.keys(store)) {
    for (const role of Object.keys(store[clientId])) {
      const { updatedAt, tree } = store[clientId][role];
      result.push({ clientId, role, updatedAt, tree });
    }
  }
  // Most recent first
  return result.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt));
}

