import { useEffect, useState } from 'react'
import { api, ingestAndBlend } from '../api'

export default function Dashboard(){
  const [health, setHealth] = useState<string>('')
  const [week, setWeek] = useState<number>(1)
  const [ingMsg, setIngMsg] = useState<string>('')
  useEffect(()=>{ api<{status:string}>('/api/healthz').then(r=>setHealth(r.status)).catch(()=>setHealth('error')) },[])
  const runIngest = async () => {
    setIngMsg('Running ingest...')
    try {
      const res = await ingestAndBlend(week)
      setIngMsg(`Done. blended=${res.blended}, FP=${res.counts?.fantasypros}, ADP=${res.counts?.adp}`)
    } catch (e:any) {
      setIngMsg(`Failed: ${e?.message||e}`)
    }
  }
  return (
    <div className="space-y-3">
      <div className="p-3 card">Health: {health}</div>
      <div className="p-3 card space-y-2">
        <div className="font-semibold">Quick Actions</div>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={()=>fetch('/api/alerts/test',{method:'POST'})} className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded">Test Slack</button>
          <div className="flex items-center gap-2">
            <label>Week <input className="border p-1 w-16" value={week} onChange={e=>setWeek(Number(e.target.value))}/></label>
            <button onClick={runIngest} className="px-3 py-1 bg-blue-600 text-white rounded">Ingest + Blend</button>
          </div>
        </div>
        {ingMsg && <div className="text-sm text-gray-700 dark:text-gray-300">{ingMsg}</div>}
      </div>
    </div>
  )
}
