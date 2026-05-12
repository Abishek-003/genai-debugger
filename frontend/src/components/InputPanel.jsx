import { useState } from 'react'

export default function InputPanel({ onSubmit, loading }) {
  const [query, setQuery] = useState('')
  const [code, setCode]   = useState('')
  const [logs, setLogs]   = useState('')

  const ta = {
    width:'100%', background:'var(--surface2)',
    border:'1px solid var(--border)', borderRadius:'8px',
    padding:'0.75rem 1rem', color:'var(--text)',
    fontSize:'0.875rem', resize:'vertical', lineHeight:1.6
  }

  return (
    <form onSubmit={e => { e.preventDefault(); onSubmit({query,code,logs}) }}
      style={{ background:'var(--surface)', border:'1px solid var(--border)',
        borderRadius:'12px', padding:'1.5rem', height:'100%',
        display:'flex', flexDirection:'column', gap:'1.25rem' }}>

      <div style={{ display:'flex', alignItems:'center', gap:'0.75rem',
        paddingBottom:'1rem', borderBottom:'1px solid var(--border)' }}>
        <span style={{ fontSize:'1.25rem' }}>🐛</span>
        <span style={{ fontWeight:700, fontSize:'1.1rem' }}>GenAI Debugger</span>
        <span style={{ marginLeft:'auto', fontSize:'0.7rem', fontFamily:'var(--mono)',
          color:'var(--muted)', background:'var(--surface2)',
          padding:'2px 8px', borderRadius:'6px', border:'1px solid var(--border)' }}>
          deepseek-coder:6.7b
        </span>
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:'0.375rem' }}>
        <label style={{ fontSize:'0.875rem', fontWeight:500, color:'var(--muted)' }}>
          Question <span style={{color:'var(--error)'}}>*</span>
        </label>
        <textarea style={{...ta, minHeight:'80px'}}
          placeholder="e.g. Why is my FastAPI endpoint returning 422?"
          value={query} onChange={e=>setQuery(e.target.value)}
          maxLength={2000} required />
        <span style={{ textAlign:'right', fontSize:'0.75rem',
          color: query.length > 1900 ? 'var(--warning)' : 'var(--faint)' }}>
          {2000 - query.length} chars left
        </span>
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:'0.375rem' }}>
        <label style={{ fontSize:'0.875rem', fontWeight:500, color:'var(--muted)' }}>Code Snippet</label>
        <textarea style={{...ta, fontFamily:'var(--mono)', fontSize:'0.8rem', minHeight:'150px'}}
          placeholder="Paste your code here..."
          value={code} onChange={e=>setCode(e.target.value)} maxLength={10000} />
      </div>

      <div style={{ display:'flex', flexDirection:'column', gap:'0.375rem' }}>
        <label style={{ fontSize:'0.875rem', fontWeight:500, color:'var(--muted)' }}>Logs / Stack Trace</label>
        <textarea style={{...ta, fontFamily:'var(--mono)', fontSize:'0.8rem', minHeight:'100px'}}
          placeholder="Paste error output here..."
          value={logs} onChange={e=>setLogs(e.target.value)} maxLength={5000} />
      </div>

      <button type="submit"
        disabled={loading || query.trim().length < 3}
        style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:'0.5rem',
          background:'var(--primary)', color:'#0d1117', fontWeight:700,
          fontSize:'0.9rem', padding:'0.75rem', borderRadius:'8px', marginTop:'auto',
          opacity: (loading || query.trim().length < 3) ? 0.5 : 1,
          cursor: (loading || query.trim().length < 3) ? 'not-allowed' : 'pointer' }}>
        {loading ? '⏳ Analyzing…' : '▶  Debug'}
      </button>
    </form>
  )
}