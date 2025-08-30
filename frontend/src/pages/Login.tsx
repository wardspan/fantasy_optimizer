import { useState } from 'react'
import { login, register } from '../api'

export default function Login({ onSuccess }:{ onSuccess: ()=>void }){
  const [mode,setMode]=useState<'login'|'register'>('register')
  const [email,setEmail]=useState('')
  const [password,setPassword]=useState('')
  const [error,setError]=useState('')
  const submit=async()=>{
    setError('')
    try {
      const r = mode==='login' ? await login(email, password) : await register(email, password)
      localStorage.setItem('authToken', r.token)
      onSuccess()
    } catch(e:any){ setError('Invalid credentials or already registered') }
  }
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white p-6 rounded shadow w-full max-w-sm">
        <h1 className="text-xl font-semibold mb-2">Fantasy Optimizer</h1>
        <p className="text-sm text-gray-600 mb-4">{mode==='register' ? 'Create an account to get started' : 'Sign in to continue'}</p>
        <input type="email" className="border w-full p-2 mb-3" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />
        <input type="password" className="border w-full p-2 mb-3" placeholder="Password" value={password} onChange={e=>setPassword(e.target.value)} />
        <button onClick={submit} className="w-full px-3 py-2 bg-blue-600 text-white rounded">{mode==='register' ? 'Create Account' : 'Login'}</button>
        {error && <div className="text-sm text-red-600 mt-2">{error}</div>}
        <div className="text-xs text-gray-500 mt-3">
          {mode==='register' ? (
            <>Already have an account? <a className="text-blue-600 cursor-pointer" onClick={()=>setMode('login')}>Sign in</a></>
          ) : (
            <>New here? <a className="text-blue-600 cursor-pointer" onClick={()=>setMode('register')}>Create an account</a></>
          )}
        </div>
        <div className="text-xs text-gray-500 mt-3">Later we can swap this to Clerk for managed auth in cloud.</div>
      </div>
    </div>
  )
}
