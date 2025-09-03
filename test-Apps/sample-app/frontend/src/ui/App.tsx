import React, { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

function App() {
  const [apiKey, setApiKey] = useState<string>('')
  const [saved, setSaved] = useState<boolean>(false)
  const [pingResult, setPingResult] = useState<any>(null)
  const [whoamiResult, setWhoamiResult] = useState<any>(null)

  // User auth state
  const [userToken, setUserToken] = useState<string | null>(localStorage.getItem('cid_sample_user_access_token'))
  const [userInfo, setUserInfo] = useState<any>(null)

  // Config (env with localStorage overrides for quick debugging)
  const CID_BASE_URL = useMemo(() => ((localStorage.getItem('cfg_cid_base_url') || import.meta.env.VITE_CID_BASE_URL || 'http://127.0.0.1:8000') as string).replace(/\/$/, ''), [])
  const CLIENT_ID = useMemo(() => ((localStorage.getItem('cfg_client_id') || import.meta.env.VITE_SAMPLE_APP_CLIENT_ID || 'app_sample_test_app') as string), [])
  const REDIRECT_URI = useMemo(() => ((localStorage.getItem('cfg_redirect_uri') || import.meta.env.VITE_REDIRECT_URI || 'http://localhost:3100/auth/callback') as string), [])
  const BACKEND_BASE_URL = useMemo(() => ((localStorage.getItem('cfg_backend_base_url') || import.meta.env.VITE_BACKEND_BASE_URL || 'http://127.0.0.1:8091') as string).replace(/\/$/, ''), [])

  useEffect(() => {
    // Handle CID callback: first check for fragment tokens (#access_token), then fallback to code exchange
    const url = new URL(window.location.href)

    // Fragment tokens (returned by CID /auth/callback)
    if (url.hash && url.hash.startsWith('#')) {
      const params = new URLSearchParams(url.hash.slice(1))
      const at = params.get('access_token')
      const rt = params.get('refresh_token')
      const st = params.get('state')
      const stored = localStorage.getItem('oauth_state')
      if (at) {
        if (stored && st && stored !== st) {
          alert('State mismatch on callback')
        }
        localStorage.removeItem('oauth_state')
        localStorage.setItem('cid_sample_user_access_token', at)
        if (rt) localStorage.setItem('cid_sample_user_refresh_token', rt)
        setUserToken(at)
        window.history.replaceState({}, document.title, '/')
        return
      }
    }

    // Authorization code exchange (if CID is configured to return code instead of fragment)
    if (url.pathname === '/auth/callback') {
      const code = url.searchParams.get('code')
      const state = url.searchParams.get('state')
      const stored = localStorage.getItem('oauth_state')
      if (!code) return
      if (!state || state !== stored) {
        alert('Invalid state parameter from CID')
        return
      }
      localStorage.removeItem('oauth_state')
      fetch(`${CID_BASE_URL}/auth/token/exchange`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, redirect_uri: REDIRECT_URI })
      })
        .then(r => r.ok ? r.json() : r.json().then(j => Promise.reject(j)))
        .then(data => {
          if (!data.access_token) throw new Error('No access_token from CID')
          localStorage.setItem('cid_sample_user_access_token', data.access_token)
          if (data.refresh_token) localStorage.setItem('cid_sample_user_refresh_token', data.refresh_token)
          setUserToken(data.access_token)
          window.history.replaceState({}, document.title, '/')
        })
        .catch(e => {
          alert(`Exchange failed: ${e?.detail || e.message || 'Unknown error'}`)
        })
    }
  }, [CID_BASE_URL, REDIRECT_URI])

  useEffect(() => {
    // If we have user token, fetch whoami from CID (optional) to show user info
    const run = async () => {
      if (!userToken) return
      try {
        const res = await fetch(`${CID_BASE_URL}/auth/whoami`, { headers: { Authorization: `Bearer ${userToken}` } })
        if (!res.ok) throw new Error('whoami failed')
        const data = await res.json()
        setUserInfo(data)
      } catch {
        setUserInfo(null)
      }
    }
    run()
  }, [CID_BASE_URL, userToken])

  const startLogin = () => {
    // Redirect to CID (not Azure) for login as the broker
    const state = Array.from(crypto.getRandomValues(new Uint8Array(16))).map(b => b.toString(16).padStart(2, '0')).join('')
    localStorage.setItem('oauth_state', state)
    const url = new URL(`${CID_BASE_URL}/auth/login`)
    url.searchParams.append('client_id', CLIENT_ID)
    url.searchParams.append('app_redirect_uri', REDIRECT_URI)
    url.searchParams.append('state', state)
    window.location.href = url.toString()
  }

  const logoutUser = () => {
    localStorage.removeItem('cid_sample_user_access_token')
    localStorage.removeItem('cid_sample_user_refresh_token')
    setUserToken(null)
    setUserInfo(null)
  }

  const saveKey = () => {
    if (!apiKey.startsWith('cids_ak_')) {
      alert('Please paste a valid CID API key (starts with cids_ak_)')
      return
    }
    localStorage.setItem('cid_sample_app_api_key', apiKey)
    setSaved(true)
    alert('API key saved locally for this sample app.')
  }

  const loadKey = (): string | null => {
    return localStorage.getItem('cid_sample_app_api_key')
  }

  const callBackendWithApiKey = async (path: string) => {
    const key = loadKey()
    if (!key) {
      alert('No API key saved yet.')
      return
    }
    try {
      const res = await axios.get(`${BACKEND_BASE_URL}${path}` , {
        headers: { Authorization: `Bearer ${key}` }
      })
      return res.data
    } catch (e: any) {
      alert(e?.response?.data?.detail || e.message)
    }
  }

  const callBackendWithUserToken = async (path: string) => {
    if (!userToken) {
      alert('Not logged in as a user')
      return
    }
    try {
      const res = await axios.get(`${BACKEND_BASE_URL}${path}` , {
        headers: { Authorization: `Bearer ${userToken}` }
      })
      return res.data
    } catch (e: any) {
      alert(e?.response?.data?.detail || e.message)
    }
  }

  return (
    <div style={{ padding: 20, fontFamily: 'system-ui, sans-serif' }}>
      <h1>CID Sample App (Frontend)</h1>

      <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
        {/* API Key auth controls */}
        <div style={{ flex: '1 1 380px' }}>
          <h2 style={{ marginTop: 0 }}>App-to-App (API Key)</h2>
          <div style={{ marginBottom: 16 }}>
            <label style={{ display: 'block', marginBottom: 8 }}>Paste App API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="cids_ak_..."
              style={{ width: '100%', maxWidth: 480, padding: 8 }}
            />
            <div style={{ marginTop: 8 }}>
              <button onClick={saveKey}>Save Key</button>
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <button onClick={async () => setPingResult(await callBackendWithApiKey('/secure/ping'))}>Test Secure Ping</button>
            <button style={{ marginLeft: 8 }} onClick={async () => setWhoamiResult(await callBackendWithApiKey('/whoami'))}>Who Am I</button>
          </div>

          {saved && <div style={{ color: 'green', marginBottom: 16 }}>Key saved.</div>}
        </div>

        {/* User auth controls */}
        <div style={{ flex: '1 1 380px' }}>
          <h2 style={{ marginTop: 0 }}>User Login (via CID/OAuth)</h2>
          {!userToken ? (
            <div>
              <p>Login will redirect to Microsoft and return here at {REDIRECT_URI}. Ensure this redirect URI is registered on the CID Azure app.</p>
              <button onClick={startLogin}>Login with CID</button>
            </div>
          ) : (
            <div>
              <div style={{ marginBottom: 8 }}>Logged in.</div>
              {userInfo && (
                <pre style={{ background: '#f6f8fa', padding: 10, borderRadius: 6, maxHeight: 220, overflow: 'auto' }}>{JSON.stringify(userInfo, null, 2)}</pre>
              )}
              <div style={{ marginTop: 8 }}>
                <button onClick={async () => setPingResult(await callBackendWithUserToken('/secure/ping'))}>Test Secure Ping (User)</button>
                <button style={{ marginLeft: 8 }} onClick={async () => setWhoamiResult(await callBackendWithUserToken('/whoami'))}>Who Am I (User)</button>
                <button style={{ marginLeft: 8 }} onClick={logoutUser}>Logout</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {pingResult && (
        <div>
          <h3>Secure Ping Result</h3>
          <pre style={{ background: '#f6f8fa', padding: 10, borderRadius: 6 }}>{JSON.stringify(pingResult, null, 2)}</pre>
        </div>
      )}

      {whoamiResult && (
        <div>
          <h3>Who Am I</h3>
          <pre style={{ background: '#f6f8fa', padding: 10, borderRadius: 6 }}>{JSON.stringify(whoamiResult, null, 2)}</pre>
        </div>
      )}
    </div>
  )
}

export default App

