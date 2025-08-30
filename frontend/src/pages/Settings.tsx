import { useEffect, useState } from 'react'
import ImportCSV from '../components/ImportCSV'
import { getSettings, saveSettings } from '../api'

export default function Settings(){
  const [currentWeek, setCurrentWeek] = useState<number>(1)
  const [msg, setMsg] = useState('')
  useEffect(()=>{ (async()=>{
    try{ const s = await getSettings(); const w = Number((s.data||{}).current_week||1); setCurrentWeek(w)}catch{}
  })() },[])
  const onSave = async ()=>{
    try { await saveSettings({ current_week: currentWeek }); setMsg('Saved') } catch(e:any){ setMsg(e.message||'Failed') }
    setTimeout(()=>setMsg(''), 1500)
  }
  return (
    <div className="space-y-4">
      <div className="card p-3">
        <h3 className="font-semibold mb-2">League Week</h3>
        <div className="flex items-center gap-2">
          <label>Current Week <input className="border p-1 w-20" type="number" min={1} max={18} value={currentWeek} onChange={e=>setCurrentWeek(Number(e.target.value))} /></label>
          <button onClick={onSave} className="px-3 py-1 bg-blue-600 text-white rounded">Save</button>
          {msg && <span className="text-sm text-gray-600">{msg}</span>}
        </div>
        <div className="text-xs text-gray-600 mt-1">Automation (ingest, weather, Coach Mode) uses this to target the right slate.</div>
      </div>
      <div className="card p-3">
        <h3 className="font-semibold mb-2">Roster Import</h3>
        <ImportCSV />
      </div>
      <div className="card p-3">
        <h3 className="font-semibold mb-2">Provider Weights</h3>
        <p>Edit weights via API or DB; defaults are ESPN 0.6 / FP 0.4.</p>
      </div>
    </div>
  )
}
