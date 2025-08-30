import { useState } from 'react'
import { api } from '../api'

export default function ImportCSV(){
  const [csv, setCsv] = useState('name,position,team,status\nPatrick Mahomes,QB,KC,start')
  const [msg, setMsg] = useState('')
  const onSubmit = async () => {
    const res = await api<{ok:boolean,count:number}>('/api/roster/import',{ method:'POST', body: JSON.stringify({ csv }) })
    setMsg(`Imported ${res.count} rows`)
  }
  return (
    <div className="space-y-2">
      <textarea value={csv} onChange={e=>setCsv(e.target.value)} className="w-full h-32 border p-2" />
      <button onClick={onSubmit} className="px-3 py-1 bg-blue-600 text-white rounded">Import</button>
      {msg && <div className="text-green-700">{msg}</div>}
    </div>
  )
}

