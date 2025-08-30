import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Waivers(){
  const [week,setWeek]=useState(1)
  const [recs,setRecs]=useState<any[]>([])
  const run=()=> api<{recs:any[]}>(`/api/waivers/suggestions?week=${week}`).then(r=>setRecs(r.recs))
  useEffect(()=>{ run() },[])
  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-center">
        <label>Week <input className="border p-1 w-16" value={week} onChange={e=>setWeek(Number(e.target.value))}/></label>
        <button onClick={run} className="px-3 py-1 bg-blue-600 text-white rounded">Suggest</button>
      </div>
      <div className="bg-white p-3 rounded shadow">
        <table className="w-full text-sm">
          <thead><tr><th className="text-left">Player</th><th>Pos</th><th>VORP Δ</th><th>FAAB</th><th>Why</th></tr></thead>
          <tbody>
            {recs.map((r,i)=> (
              <tr key={i} className="border-t"><td className="py-1">{r.name}</td><td className="text-center">{r.position}</td><td className="text-center">{r.vorp_delta}</td><td className="text-center">{r.faab_bid}</td><td>{r.rationale}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

