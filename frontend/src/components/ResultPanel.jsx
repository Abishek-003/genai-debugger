import { useState } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

function parseBlocks(text) {
  const parts = []; const re = /```(?:\w+)?\n([\s\S]*?)```/g
  let last = 0, m
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push({ type:'text', content: text.slice(last, m.index) })
    parts.push({ type:'code', content: m[1].trimEnd() })
    last = re.lastIndex
  }
  if (last < text.length) parts.push({ type:'text', content: text.slice(last) })
  return parts
}

function CopyBtn({ text }) {
  const [done, setDone] = useState(false)
  const copy = () => { navigator.clipboard.writeText(text); setDone(true); setTimeout(()=>setDone(false),2000) }
  return (
    <button onClick={copy} style={{ fontSize:'0.75rem', color:'var(--muted)',
      padding:'2px 8px', borderRadius:'4px', border:'1px solid var(--border)' }}>
      {done ? '✓ Copied' : 'Copy'}
    </button>
  )
}

const TABS = [
  { key:'final_answer',   label:'✅ Final Answer'   },
  { key:'critique',       label:'🔍 Critique'       },
  { key:'initial_answer', label:'💡 Initial Answer' },
]

export default function ResultPanel({ result, error, loading }) {
  const [tab, setTab] = useState('final_answer')

  const box = { background:'var(--surface)', border:'1px solid var(--border)',
    borderRadius:'12px', minHeight:'calc(100dvh - 3rem)',
    display:'flex', flexDirection:'column', overflow:'hidden' }

  if (loading) return (
    <div style={{...box, alignItems:'center', justifyContent:'center', gap:'1rem'}}>
      <style>{`@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      <div style={{ width:36, height:36, border:'3px solid var(--border)',
        borderTopColor:'var(--primary)', borderRadius:'50%',
        animation:'spin 0.8s linear infinite' }} />
      <p style={{color:'var(--muted)', fontSize:'0.9rem'}}>Running pipeline… (~30s)</p>
    </div>
  )

  if (error) return (
    <div style={{...box, alignItems:'center', justifyContent:'center', gap:'0.75rem', padding:'2rem'}}>
      <span style={{fontSize:'2rem'}}>❌</span>
      <p style={{fontWeight:600}}>Request Failed</p>
      <p style={{color:'var(--muted)', fontSize:'0.875rem', textAlign:'center'}}>{error}</p>
    </div>
  )

  if (!result) return (
    <div style={{...box, alignItems:'center', justifyContent:'center', gap:'0.75rem', padding:'2rem'}}>
      <span style={{fontSize:'3rem'}}>🤖</span>
      <p style={{fontWeight:600}}>No results yet</p>
      <p style={{color:'var(--muted)', fontSize:'0.875rem', textAlign:'center', maxWidth:'36ch'}}>
        Fill in the form on the left and hit Debug.
      </p>
    </div>
  )

  return (
    <div style={box}>
      <div style={{ display:'flex', borderBottom:'1px solid var(--border)', padding:'0 1rem', gap:'0.25rem' }}>
        {TABS.map(t => (
          <button key={t.key} onClick={()=>setTab(t.key)} style={{
            padding:'0.75rem 1rem', fontSize:'0.875rem', fontWeight:500,
            color: tab===t.key ? 'var(--primary)' : 'var(--muted)',
            borderBottom: tab===t.key ? '2px solid var(--primary)' : '2px solid transparent',
            whiteSpace:'nowrap', transition:'color 0.15s' }}>
            {t.label}
          </button>
        ))}
      </div>
      <div style={{ flex:1, overflowY:'auto', padding:'1.5rem',
        display:'flex', flexDirection:'column', gap:'1rem' }}>
        {parseBlocks(result[tab]).map((b,i) =>
          b.type === 'code' ? (
            <div key={i} style={{ borderRadius:'8px', overflow:'hidden', border:'1px solid var(--border)' }}>
              <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center',
                padding:'0.375rem 1rem', background:'var(--surface2)', borderBottom:'1px solid var(--border)' }}>
                <span style={{ fontSize:'0.75rem', fontFamily:'var(--mono)', color:'var(--muted)' }}>python</span>
                <CopyBtn text={b.content} />
              </div>
              <SyntaxHighlighter language="python" style={oneDark} showLineNumbers
                customStyle={{ margin:0, background:'#0d1117', fontSize:'0.8rem', padding:'1rem' }}>
                {b.content}
              </SyntaxHighlighter>
            </div>
          ) : (
            <pre key={i} style={{ fontFamily:'inherit', fontSize:'0.9rem',
              color:'var(--text)', whiteSpace:'pre-wrap', lineHeight:1.75 }}>
              {b.content.trim()}
            </pre>
          )
        )}
      </div>
    </div>
  )
}