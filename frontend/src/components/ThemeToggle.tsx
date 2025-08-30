import { useEffect, useRef, useState } from 'react'

type Mode = 'light' | 'dark' | 'system'

export default function ThemeToggle(){
  const [mode,setMode] = useState<Mode>('system')
  const [open,setOpen]=useState(false)
  const ref = useRef<HTMLDivElement|null>(null)
  useEffect(()=>{
    try{
      const saved = localStorage.getItem('theme') as Mode | null
      if (saved) setMode(saved)
    }catch{}
  },[])
  useEffect(()=>{
    const el = document.documentElement
    if (mode==='system'){
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      el.classList.toggle('dark', prefersDark)
    } else {
      el.classList.toggle('dark', mode==='dark')
    }
    try { localStorage.setItem('theme', mode) } catch{}
  },[mode])
  useEffect(()=>{
    const onDoc = (e:MouseEvent)=>{ if (ref.current && !ref.current.contains(e.target as any)) setOpen(false) }
    document.addEventListener('mousedown', onDoc)
    return ()=>document.removeEventListener('mousedown', onDoc)
  },[])
  const icon = mode==='light' ? '☀️' : mode==='dark' ? '🌙' : '💻'
  return (
    <div className="relative" ref={ref}>
      <button title="Theme" onClick={()=>setOpen(!open)} className="px-2 py-1 rounded text-sm bg-gray-200 dark:bg-gray-700">{icon}</button>
      {open && (
        <div className="absolute right-0 mt-1 p-1 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded shadow text-sm">
          <button onClick={()=>{setMode('light'); setOpen(false)}} className={`block px-3 py-1 rounded w-full text-left ${mode==='light'?'bg-blue-600 text-white':''}`}>☀️ Light</button>
          <button onClick={()=>{setMode('dark'); setOpen(false)}} className={`block px-3 py-1 rounded w-full text-left ${mode==='dark'?'bg-blue-600 text-white':''}`}>🌙 Dark</button>
          <button onClick={()=>{setMode('system'); setOpen(false)}} className={`block px-3 py-1 rounded w-full text-left ${mode==='system'?'bg-blue-600 text-white':''}`}>💻 System</button>
        </div>
      )}
    </div>
  )
}
