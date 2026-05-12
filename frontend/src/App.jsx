import { useState } from 'react'
import { submitQuery } from './api/query.js'
import InputPanel from './components/InputPanel.jsx'
import ResultPanel from './components/ResultPanel.jsx'

export default function App() {
  const [result, setResult]   = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState(null)

  const handleSubmit = async (payload) => {
    setLoading(true); setError(null); setResult(null)
    try { setResult(await submitQuery(payload)) }
    catch (err) { setError(err.message) }
    finally { setLoading(false) }
  }

  return (
    <div style={{ display:'grid', gridTemplateColumns:'420px 1fr',
      gap:'1.5rem', minHeight:'100dvh', padding:'1.5rem',
      maxWidth:'1400px', margin:'0 auto' }}>
      <aside style={{ position:'sticky', top:'1.5rem', height:'calc(100dvh - 3rem)' }}>
        <InputPanel onSubmit={handleSubmit} loading={loading} />
      </aside>
      <main>
        <ResultPanel result={result} error={error} loading={loading} />
      </main>
    </div>
  )
}