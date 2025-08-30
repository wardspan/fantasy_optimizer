import { useEffect, useState } from 'react'
import { api, LineupResp, importSchedule, updateWeather } from '../api'

export default function Lineup(){
  const [week,setWeek]=useState(1)
  const [riskData,setRiskData]=useState<LineupResp|null>(null)
  const [expData,setExpData]=useState<LineupResp|null>(null)
  const [schedCsv, setSchedCsv] = useState('team,opponent,home,kickoff_iso\nKC,CIN,1,2025-09-07T17:00:00Z')
  const [msg, setMsg] = useState('')
  const run=()=>{
    api<LineupResp>(`/api/lineup/optimal?week=${week}&objective=risk`).then(setRiskData)
    api<LineupResp>(`/api/lineup/optimal?week=${week}&objective=expected`).then(setExpData)
  }
  useEffect(()=>{ run() },[])
  const renderCol = (title:string, data:LineupResp|null) => (
    <div className="bg-white p-3 rounded shadow">
      <h3 className="font-semibold mb-2">{title}</h3>
      {!data ? <div className="text-sm text-gray-500">Computing…</div> : (
        <>
          <div className="mb-2 text-xs text-gray-600">Starters selected to maximize {title.toLowerCase()} points subject to roster rules.</div>
          <ul className="space-y-1">
            {data.starters.map((s:any,i)=> {
              const injury = (s.injury||'').toLowerCase()
              const injCls = injury==='out' ? 'bg-red-100 text-red-800' : injury==='doubtful' ? 'bg-orange-100 text-orange-800' : injury==='questionable' ? 'bg-yellow-100 text-yellow-800' : ''
              const qb = data.starters.find((p:any)=>p.position==='QB')
              const isStack = qb && qb.team && s.team && s.position && (s.position==='WR' || s.position==='TE') && qb.team===s.team
              const wx = s.weather
              const wxText = wx ? `${Math.round((wx.temp_c*9/5)+32)}°F${wx.precip_prob!=null? ' '+wx.precip_prob+'%':''}` : null
              const wxCls = wx && wx.precip_prob!=null ? (wx.precip_prob>=50 ? 'bg-sky-200 text-sky-900' : 'bg-sky-100 text-sky-800') : 'bg-gray-100 text-gray-700'
              return (
                <li key={i} className="flex justify-between items-center border-b py-1">
                  <span className="flex items-center gap-2">
                    <span className="text-gray-600 mr-1">{s.position}</span>
                    <span className="font-medium">{s.name}</span>
                    {s.team && <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">{s.team}</span>}
                    {injCls && <span className={`text-[10px] px-1.5 py-0.5 rounded ${injCls}`}>{s.injury}</span>}
                    {isStack && <span className="text-[10px] px-1.5 py-0.5 rounded bg-purple-100 text-purple-800" title="Stacked with your QB">Stack</span>}
                    {s.home!=null && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">{s.home? 'Home':'Away'}</span>}
                    {wxText && <span className={`text-[10px] px-1.5 py-0.5 rounded ${wxCls}`} title="Kickoff window weather">{wxText}</span>}
                  </span>
                  <span className="inline-block px-2 py-0.5 rounded-full bg-blue-100 text-blue-800" title="Objective value">{s.value}</span>
                </li>
              )
            })}
          </ul>
          <div className="mt-3">
            <h4 className="font-semibold text-sm">Bench (priority)</h4>
            <ul className="space-y-1 text-sm">
              {data.bench.map((s:any,i)=> {
                const injury = (s.injury||'').toLowerCase()
                const injCls = injury==='out' ? 'bg-red-100 text-red-800' : injury==='doubtful' ? 'bg-orange-100 text-orange-800' : injury==='questionable' ? 'bg-yellow-100 text-yellow-800' : ''
                const wx = s.weather
                const wxText = wx ? `${Math.round((wx.temp_c*9/5)+32)}°F${wx.precip_prob!=null? ' '+wx.precip_prob+'%':''}` : null
                const wxCls = wx && wx.precip_prob!=null ? (wx.precip_prob>=50 ? 'bg-sky-200 text-sky-900' : 'bg-sky-100 text-sky-800') : 'bg-gray-100 text-gray-700'
                return (
                  <li key={i} className="flex justify-between items-center border-b py-1">
                    <span className="flex items-center gap-2">
                      <span className="text-gray-600 mr-1">{s.position}</span>
                      <span>{s.name}</span>
                      {s.team && <span className="text-[10px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-700">{s.team}</span>}
                      {injCls && <span className={`text-[10px] px-1.5 py-0.5 rounded ${injCls}`}>{s.injury}</span>}
                      {s.home!=null && <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-800">{s.home? 'Home':'Away'}</span>}
                      {wxText && <span className={`text-[10px] px-1.5 py-0.5 rounded ${wxCls}`} title="Kickoff window weather">{wxText}</span>}
                    </span>
                    <span className="text-gray-700">{s.value}</span>
                  </li>
                )
              })}
            </ul>
          </div>
        </>
      )}
    </div>
  )
  return (
    <div className="space-y-3">
      <div className="card p-3 text-sm text-gray-800 dark:text-gray-200">
        <div className="font-semibold mb-1">Lineup objectives</div>
        <ul className="list-disc pl-5 space-y-1">
          <li><span className="font-semibold">Risk-Adjusted</span>: prefers steadier players by subtracting a risk penalty from projections. Good when you’re favored or want consistency.</li>
          <li><span className="font-semibold">Projected</span>: pure expected points with no risk penalty. Useful when you’re an underdog and need ceiling.</li>
          <li><span className="font-semibold">How to use</span>: compare the two columns; differences highlight swaps where volatility matters (e.g., boom/bust WRs).</li>
        </ul>
      </div>
      <div className="flex gap-2 items-center">
        <label>Week <input className="border p-1 w-16" value={week} onChange={e=>setWeek(Number(e.target.value))}/></label>
        <button onClick={run} className="px-3 py-1 bg-blue-600 text-white rounded">Optimize</button>
        <button onClick={async()=>{ setMsg('Updating weather...'); try { const r = await updateWeather(week); setMsg(`Weather updated for ${r.updated_games} games`)} catch(e:any){ setMsg(e.message||'Failed') } }} className="px-3 py-1 bg-sky-600 text-white rounded">Fetch Weather</button>
      </div>
      <div className="card p-3 text-sm text-gray-800 dark:text-gray-200">
        <div className="font-semibold mb-1">Schedule Import (optional)</div>
        <div className="text-xs text-gray-600 mb-2">Paste CSV: team, opponent, home(1/0), kickoff_iso(optional). Import before fetching weather.</div>
        <textarea className="w-full border p-2 h-24" value={schedCsv} onChange={e=>setSchedCsv(e.target.value)} />
        <div className="mt-2 flex items-center gap-2">
          <button onClick={async()=>{ setMsg('Importing schedule...'); try { const r = await importSchedule(week, schedCsv); setMsg(`Imported ${r.imported} rows`) } catch(e:any){ setMsg(e.message||'Failed') } }} className="px-3 py-1 bg-gray-800 text-white rounded">Import Schedule</button>
          {msg && <span className="text-xs text-gray-700">{msg}</span>}
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {renderCol('Risk-Adjusted', riskData)}
        {renderCol('Projected', expData)}
      </div>
    </div>
  )
}
