import { useState } from 'react'
import { login } from '../api'

export default function Login({ onSuccess }:{ onSuccess: ()=>void }){
  const [password,setPassword]=useState('')
  const [error,setError]=useState('')
  const submit=async()=>{
    setError('')
    try {
      const r = await login(password)
      localStorage.setItem('authToken', r.token)
      onSuccess()
    } catch(e:any){ setError('Invalid password') }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-6 rounded shadow w-full max-w-sm">
        <h1 className="text-xl font-semibold mb-2">Fantasy Optimizer</h1>
        <p className="text-sm text-gray-600 mb-4">Sign in to continue</p>
        <input type="password" className="border w-full p-2 mb-3" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
        <button onClick={submit} className="w-full px-3 py-2 bg-blue-600 text-white rounded">Login</button>
        {error && <div className="text-sm text-red-600 mt-2">{error}</div>}
        <div className="text-xs text-gray-500 mt-3">Tip: set APP_PASSWORD and AUTH_SECRET on your server (e.g., Vercel env vars).</div>
      </div>
    </div>
  )
}

