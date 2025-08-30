import { useEffect, useState } from 'react'
import { api } from '../api'

export default function DraftHelper(){
  const [round,setRound]=useState(1)
  const [pick,setPick]=useState(1)
  const [data,setData]=useState<any>({})
  const run=()=> api<any>(`/api/draft/best-picks?round=${round}&pick=${pick}`).then(setData)
  useEffect(()=>{ run() },[])
  const quantile = (arr:number[], q:number) => {
    if (!arr.length) return 0
    const a = [...arr].sort((x,y)=>x-y)
    const pos = (a.length-1)*q
    const base = Math.floor(pos), rest = pos-base
    if (a[base+1]!==undefined) return a[base] + rest*(a[base+1]-a[base])
    return a[base]
  }
  return (
    <div className="space-y-2">
      <div className="card p-3 text-sm text-gray-800 dark:text-gray-200">
        <div className="font-semibold mb-1">How to read this</div>
        <ul className="list-disc pl-5 space-y-1">
          <li><span className="font-semibold">VORP</span> = Value Over Replacement: projected points minus a baseline starter at the same position (QB12, RB24, WR24, TE12, K12, D/ST12).</li>
          <li><span className="font-semibold">Score</span>: Based on VORP for this round plus a small penalty for big reaches. Higher is better.</li>
          <li><span className="font-semibold">ADP</span>: Average draft position from public data. We show both FantasyPros (FP) and ESPN (when available). “N/A” means no consensus (often K/DST or deep sleepers).</li>
          <li><span className="font-semibold">Reach</span>: Calculated vs ESPN ADP if available, otherwise FP ADP.</li>
          <li><span className="font-semibold">Reach</span>: How many rounds earlier than ADP this pick would be (0 is “on market”). Small reaches are fine when filling needs or avoiding positional runs.</li>
          <li><span className="font-semibold">What to look for</span>: prioritize high <span className="font-semibold">Score</span>, fill scarce positions (RB/TE), avoid stacking bye weeks, and don’t panic—if scores are similar, pick the position you need.</li>
          <li><span className="font-semibold">Positions</span>: QB = Quarterback, RB = Running Back, WR = Wide Receiver, TE = Tight End, K = Kicker, D/ST = Team Defense/Special Teams.</li>
        </ul>
      </div>
      <div className="flex gap-2 items-center">
        <label>Round <input className="border p-1 w-16" value={round} onChange={e=>setRound(Number(e.target.value))}/></label>
        <label>Pick <input className="border p-1 w-16" value={pick} onChange={e=>setPick(Number(e.target.value))}/></label>
        <button onClick={run} title="Recalculate best picks for the chosen round and pick using current projections and ADP."
                className="px-3 py-1 bg-blue-600 text-white rounded">Compute</button>
      </div>
      <div className="text-xs text-gray-600 text-muted-dark">Compute updates the lists below for the selected round and pick; it does not auto‑draft or change your roster.</div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {Object.entries(data).map(([pos,list]:any)=> {
          const scores = list.map((r:any)=> Number(r.score)||0)
          const p75 = quantile(scores, 0.75)
          const p90 = quantile(scores, 0.90)
          return (
            <div key={pos} className="card p-3">
              <h3 className="font-semibold mb-2">{pos}</h3>
              <table className="w-full text-sm text-base-dark">
                <thead>
                  <tr className="text-left text-gray-500 dark:text-gray-300"><th>Player</th><th className="text-right">Score</th><th className="text-right">VORP</th><th className="text-right">ADP (FP)</th><th className="text-right">ADP (ESPN)</th><th className="text-right">Reach</th></tr>
                </thead>
                <tbody>
                  {list.map((r:any)=> {
                    const s = Number(r.score)||0
                    const reach = Number(r.reach)||0
                    const adpFp = (r.adp_fp===null || r.adp_fp===undefined || Number(r.adp_fp)>=900) ? 'N/A' : r.adp_fp
                    const adpEspn = (r.adp_espn===null || r.adp_espn===undefined || Number(r.adp_espn)>=900) ? 'N/A' : r.adp_espn
                    const scoreBadgeCls = s>=p90
                      ? 'bg-green-600 text-white'
                      : s>=p75
                        ? 'bg-green-100 text-green-800 dark:bg-green-900/50 dark:text-green-200'
                        : 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200'
                    const reachBadgeCls = reach<=0
                      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-200'
                      : reach<=1
                        ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-200'
                        : reach<=2
                          ? 'bg-orange-100 text-orange-800 dark:bg-orange-900/40 dark:text-orange-200'
                          : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-200'
                    const rowHl = s>=p90 ? 'bg-green-50 dark:bg-green-900/30' : reach>2 ? 'bg-orange-50 dark:bg-orange-900/30' : ''
                    return (
                      <DraftRow key={r.player_id} r={{...r, s, adpFp, adpEspn}} scoreBadgeCls={scoreBadgeCls} reachBadgeCls={reachBadgeCls} rowHl={rowHl} />
                    )
                  })}
                </tbody>
              </table>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function DraftRow({ r, scoreBadgeCls, reachBadgeCls, rowHl }:{ r:any, scoreBadgeCls:string, reachBadgeCls:string, rowHl:string }){
  const [hover, setHover] = useState(false)
  return (
    <tr onMouseEnter={()=>setHover(true)} onMouseLeave={()=>setHover(false)} className={`border-t relative ${rowHl}`}>
      <td className="py-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">{r.name}</span>
          {r.team && <span className="text-xs bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200 px-1.5 py-0.5 rounded">{r.team}</span>}
        </div>
        {hover && (
          <div className="absolute z-10 mt-1 p-2 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow text-xs w-64 text-base-dark">
            <div className="font-semibold mb-1">Why this pick?</div>
            <div className="mb-1">VORP: <span className="font-medium">{r.vorp}</span> — value over replacement.</div>
            <div className="mb-1">ADP FP/ESPN: <span className="font-medium">{r.adpFp}</span> / <span className="font-medium">{r.adpEspn}</span></div>
            <div className="mb-1">Reach: <span className="font-medium">{r.reach}</span> — small reaches are OK to fill needs.</div>
            {r.rationale && <div className="text-gray-600 text-muted-dark">{r.rationale}</div>}
          </div>
        )}
      </td>
      <td className="text-right"><span className={`inline-block px-2 py-0.5 rounded-full ${scoreBadgeCls}`}>{r.s}</span></td>
      <td className="text-right"><span className="inline-block px-2 py-0.5 rounded-full bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-200">{r.vorp}</span></td>
      <td className="text-right text-gray-700 dark:text-gray-200">{r.adpFp}</td>
      <td className="text-right text-gray-700 dark:text-gray-200">{r.adpEspn}</td>
      <td className="text-right"><span className={`inline-block px-2 py-0.5 rounded-full ${reachBadgeCls}`}>{r.reach}</span></td>
    </tr>
  )
}
