import { useState } from 'react'
import { api } from '../api'

export default function WhatIf(){
  const [week,setWeek]=useState(1)
  const [pid,setPid]=useState<number>(1)
  const [expected,setExpected]=useState<number>(20)
  const [lambdaRisk,setLambdaRisk]=useState<number>(0.35)
  const [resp,setResp]=useState<any>(null)
  const run=()=>{
    api('/api/whatif/lineup',{method:'POST', body: JSON.stringify({week, objective:'risk', overrides: {[pid]:{expected}}, lambda_risk: lambdaRisk})}).then(setResp)
  }
  return (
    <div className="space-y-2">
      <div className="flex gap-2 items-center">
        <label>Week <input className="border p-1 w-16" value={week} onChange={e=>setWeek(Number(e.target.value))}/></label>
        <label>Player ID <input className="border p-1 w-24" value={pid} onChange={e=>setPid(Number(e.target.value))}/></label>
        <label>Expected <input className="border p-1 w-24" value={expected} onChange={e=>setExpected(Number(e.target.value))}/></label>
        <label>λ <input className="border p-1 w-24" value={lambdaRisk} onChange={e=>setLambdaRisk(Number(e.target.value))}/></label>
        <button onClick={run} className="px-3 py-1 bg-blue-600 text-white rounded">What-if</button>
      </div>
      {resp && <pre className="bg-white p-3 rounded shadow overflow-auto text-xs">{JSON.stringify(resp,null,2)}</pre>}
    </div>
  )
}

