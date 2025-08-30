import { useEffect, useState } from 'react'
import Dashboard from './pages/Dashboard'
import Lineup from './pages/Lineup'
import DraftHelper from './pages/DraftHelper'
import Waivers from './pages/Waivers'
import Trades from './pages/Trades'
import WhatIf from './pages/WhatIf'
import Settings from './pages/Settings'
import Reports from './pages/Reports'
import Login from './pages/Login'
import Layout from './components/Layout'

type Page = 'Dashboard' | 'Lineup' | 'Draft' | 'Waivers' | 'Trades' | 'WhatIf' | 'Settings' | 'Reports'

export default function App() {
  const [page, setPage] = useState<Page>('Dashboard')
  const [authed,setAuthed]=useState<boolean>(!!(typeof localStorage!=='undefined' && localStorage.getItem('authToken')))
  useEffect(()=>{
    // If token exists, keep authed; otherwise show login
    setAuthed(!!localStorage.getItem('authToken'))
  },[])
  if (!authed) return <Login onSuccess={()=>setAuthed(true)} />
  return (
    <Layout page={page} setPage={setPage}>
      {page==='Dashboard' && <Dashboard />}
      {page==='Lineup' && <Lineup />}
      {page==='Draft' && <DraftHelper />}
      {page==='Waivers' && <Waivers />}
      {page==='Trades' && <Trades />}
      {page==='WhatIf' && <WhatIf />}
      {page==='Settings' && <Settings />}
      {page==='Reports' && <Reports />}
    </Layout>
  )
}
