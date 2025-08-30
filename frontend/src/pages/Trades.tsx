import { useState } from 'react'
import { api } from '../api'

export default function Trades(){
  const [playersIn,setPlayersIn]=useState('')
  const [playersOut,setPlayersOut]=useState('')
  const [resp,setResp]=useState<any>(null)
  const evalTrade=()=>{
    const inIds = playersIn.split(',').map(s=>Number(s.trim())).filter(Boolean)
    const outIds = playersOut.split(',').map(s=>Number(s.trim())).filter(Boolean)
    api('/api/trades/evaluate?week=1',{method:'POST', body: JSON.stringify({players_in: inIds, players_out: outIds})}).then(setResp)
  }
  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-center">
        <input className="border p-1 flex-1" placeholder="Player IDs in (comma separated)" value={playersIn} onChange={e=>setPlayersIn(e.target.value)} />
        <input className="border p-1 flex-1" placeholder="Player IDs out (comma separated)" value={playersOut} onChange={e=>setPlayersOut(e.target.value)} />
        <button onClick={evalTrade} className="px-3 py-1 bg-blue-600 text-white rounded">Evaluate</button>
      </div>
      {resp && <div className="bg-white p-3 rounded shadow">Fairness: {resp.fairness} | My Δ: {resp.delta_my} | Their Δ: {resp.delta_their}<div className="text-gray-600">{resp.rationale}</div></div>}
    </div>
  )
}

