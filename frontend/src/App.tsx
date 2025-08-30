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
import Modal from './components/Modal'
import { ingestAndBlend } from './api'
import { useRef } from 'react'
import { useEffect as useEff } from 'react'

type Page = 'Dashboard' | 'Lineup' | 'Draft' | 'Waivers' | 'Trades' | 'WhatIf' | 'Settings' | 'Reports'

export default function App() {
  const [page, setPage] = useState<Page>('Draft')
  const [authed,setAuthed]=useState<boolean>(!!(typeof localStorage!=='undefined' && localStorage.getItem('authToken')))
  const [modalOpen, setModalOpen] = useState(false)
  const [modalMsg, setModalMsg] = useState('')
  useEffect(()=>{
    // If token exists, keep authed; otherwise show login
    setAuthed(!!localStorage.getItem('authToken'))
  },[])
  const firstLoginRef = useRef(false)
  const handleLoginSuccess = async () => {
    setAuthed(true)
    // Kick off ingest and route to Draft
    setModalOpen(true)
    setModalMsg('Getting data ready… Pulling projections and injuries.')
    try {
      const res = await ingestAndBlend(1)
      const counts = res.counts||{}
      setModalMsg(`Blended ${res.blended} players. FP proj: ${counts.fantasypros||0}, ESPN proj: ${counts.espn||0}, ADP FP: ${counts.adp_fp||0}, ADP ESPN: ${counts.adp_espn||0}.`)
    } catch(e:any){
      setModalMsg('Data fetch hit a snag, using cached data if available.')
    }
    setTimeout(()=>{
      setModalOpen(false)
      setPage('Draft')
      firstLoginRef.current = true
    }, 800)
  }
  if (!authed) return <Login onSuccess={handleLoginSuccess} />
  return (
    <Layout page={page} setPage={setPage}>
      <Modal open={modalOpen} title="Preparing Your Draft Board">
        <div className="flex items-center gap-2">
          <span className="inline-block w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
          <span>{modalMsg}</span>
        </div>
      </Modal>
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
