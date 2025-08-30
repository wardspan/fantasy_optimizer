import { useEffect, useState } from 'react'
import ImportCSV from '../components/ImportCSV'
import { getSettings, saveSettings, ingestAndBlend } from '../api'

export default function Settings(){
  const [currentWeek, setCurrentWeek] = useState<number>(1)
  const [msg, setMsg] = useState('')
  useEffect(()=>{ (async()=>{
    try{ const s = await getSettings(); const w = Number((s.data||{}).current_week||1); setCurrentWeek(w)}catch{}
  })() },[])
  const [ingMsg, setIngMsg] = useState('')
  const runIngest = async () => {
    setIngMsg('Running ingest...')
    try { const res = await ingestAndBlend(currentWeek); setIngMsg(`Done. blended=${res.blended}, FP=${res.counts?.fantasypros}, ESPN=${res.counts?.espn}, SportsData=${res.counts?.sportsdata_proj||0}, Yahoo=${res.counts?.yahoo_proj||0}, ADP_FP=${res.counts?.adp_fp}, ADP_ESPN=${res.counts?.adp_espn}`) }
    catch(e:any){ setIngMsg(e.message||'Failed') }
  }
  const [schedCsv, setSchedCsv] = useState('team,opponent,home,kickoff_iso\n')
  const [everythingMsg, setEverythingMsg] = useState('')
  const updateEverything = async () => {
    setEverythingMsg('Updating everything...')
    try {
      const res = await fetch(`/api/admin/update-everything?week=${currentWeek}`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ schedule_csv: schedCsv }) })
      const data = await res.json()
      if (!res.ok) throw new Error(JSON.stringify(data))
      setEverythingMsg(`OK: blended=${data.counts?.blended}, schedule=${data.counts?.schedule_imported}, sportsdata_inj=${data.counts?.sportsdata_inj||0}, lineup ready.`)
    } catch(e:any){ setEverythingMsg(e.message||'Failed') }
  }
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
      <div className="card p-3">
        <h3 className="font-semibold mb-2">Ingest Data</h3>
        <div className="flex items-center gap-2">
          <button onClick={runIngest} className="px-3 py-1 bg-blue-600 text-white rounded">Ingest + Blend (Week {currentWeek})</button>
          {ingMsg && <span className="text-sm text-gray-600">{ingMsg}</span>}
        </div>
        <div className="text-xs text-gray-600 mt-1">This pulls projections (FP + ESPN), injuries, and ADPs, blends them, and updates the DB.</div>
      </div>
      <div className="card p-3">
        <h3 className="font-semibold mb-2">Integrations</h3>
        <button onClick={()=>fetch('/api/alerts/test',{method:'POST'})} className="px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded">Test Slack</button>
      </div>
      <div className="card p-3">
        <h3 className="font-semibold mb-2">Update Everything</h3>
        <div className="text-xs text-gray-600 mb-2">Optional: paste weekly schedule CSV to enrich weather/home/away.</div>
        <textarea className="w-full border p-2 h-24" value={schedCsv} onChange={e=>setSchedCsv(e.target.value)} />
        <div className="mt-2 flex items-center gap-2">
          <button onClick={updateEverything} className="px-3 py-1 bg-green-600 text-white rounded">Update Everything (Week {currentWeek})</button>
          {everythingMsg && <span className="text-sm text-gray-600">{everythingMsg}</span>}
        </div>
      </div>
    </div>
  )
}
