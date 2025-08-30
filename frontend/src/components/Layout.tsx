import ThemeToggle from './ThemeToggle'
import { useState } from 'react'

export default function Layout({ children, page, setPage }:{ children:any, page:string, setPage:(p:any)=>void }){
  const [menuOpen,setMenuOpen]=useState(false)
  const pages = ['Dashboard','Draft','Lineup','Waivers','Trades','Reports','Settings']
  const logout = ()=>{ try{ localStorage.removeItem('authToken'); location.reload() }catch{} }
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur">
        <div className="max-w-6xl mx-auto p-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <button className="md:hidden px-2 py-1 border rounded" onClick={()=>setMenuOpen(!menuOpen)}>☰</button>
            <h1 className="text-xl font-bold">Fantasy Optimizer</h1>
          </div>
          <div className="hidden md:flex items-center gap-2">
            {pages.map(p => (
              <button key={p} onClick={()=>setPage(p as any)} className={`px-2 py-1 rounded text-sm ${page===p? 'bg-blue-600 text-white':'bg-gray-200 dark:bg-gray-700'}`}>{p}</button>
            ))}
            <ThemeToggle />
            <button onClick={logout} className="px-2 py-1 rounded text-sm bg-red-600 text-white">Logout</button>
          </div>
        </div>
        {menuOpen && (
          <div className="md:hidden p-3 flex flex-wrap gap-2 border-t bg-white dark:bg-gray-900">
            {pages.map(p => (
              <button key={p} onClick={()=>{ setPage(p as any); setMenuOpen(false) }} className={`px-2 py-1 rounded text-sm ${page===p? 'bg-blue-600 text-white':'bg-gray-200 dark:bg-gray-700'}`}>{p}</button>
            ))}
            <ThemeToggle />
            <button onClick={logout} className="px-2 py-1 rounded text-sm bg-red-600 text-white">Logout</button>
          </div>
        )}
      </header>
      <main className="max-w-6xl mx-auto p-4">{children}</main>
    </div>
  )
}
