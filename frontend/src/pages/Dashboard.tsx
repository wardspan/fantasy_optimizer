import React, { useEffect, useMemo, useState } from 'react'
import { api, getMyRoster, getMyNews, getStandings, getDashboardCards } from '../api'
import Modal from '../components/Modal'

export default function Dashboard(){
  const [health, setHealth] = useState<string>('')
  const [roster,setRoster]=useState<any[]>([])
  const [news,setNews]=useState<any>({items:[]})
  const [standings,setStandings]=useState<any>({table:[]})
  const [cards,setCards]=useState<any>({injuries:[],byes:[],weather:[],late_swap:[],waivers:[],trade:[]})
  useEffect(()=>{
    api<{status:string}>('/api/healthz').then(r=>setHealth(r.status)).catch(()=>setHealth('error'))
    getMyRoster().then(setRoster).catch(()=>setRoster({roster:[]} as any))
    getMyNews().then(setNews).catch(()=>setNews({items:[]} as any))
    getStandings().then(setStandings).catch(()=>setStandings({table:[]}))
    getDashboardCards().then(setCards).catch(()=>setCards({injuries:[],byes:[],weather:[],late_swap:[],waivers:[],trade:[]}))
  },[])
  return (
    <div className="space-y-3">
      <div className="p-3 card">Health: {health}</div>
      <div className="p-3 card">
        <h3 className="font-semibold mb-2">My Team</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
          <div>
            <div className="font-semibold mb-1">Starters</div>
            <ul className="space-y-1">
              {roster.roster?.filter((r:any)=>r.status==='start').map((r:any)=> (
                <li key={r.player_id} className="flex justify-between border-b py-1"><span>{r.position} {r.name}</span><span className="text-gray-600">{r.team}</span></li>
              ))}
            </ul>
          </div>
          <div>
            <div className="font-semibold mb-1">Bench</div>
            <ul className="space-y-1">
              {roster.roster?.filter((r:any)=>r.status==='bench').map((r:any)=> (
                <li key={r.player_id} className="flex justify-between border-b py-1"><span>{r.position} {r.name}</span><span className="text-gray-600">{r.team}</span></li>
              ))}
            </ul>
          </div>
        </div>
      </div>
      <div className="p-3 card">
        <h3 className="font-semibold mb-2">League & Player News</h3>
        <Carousel>
          {news.items?.filter((x:any)=>x.kind==='news').length > 0 && (
            <div className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">📰 Player News</div>
              <ul className="text-sm text-base-dark">
                {news.items.filter((x:any)=>x.kind==='news').slice(0,3).map((n:any,i:number)=> (
                  <li key={`news-${i}`} className="border-b py-1">
                    <span className="font-medium">{n.name}</span>
                    {n.status && <span className="ml-2 badge bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">{n.status}</span>}
                    {n.note && <div className="text-xs text-muted-dark">{n.note}</div>}
                  </li>
                ))}
              </ul>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('news')}>More</a></div>
            </div>
          )}
          {/* Standings */}
          <div className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
            <div className="font-semibold mb-1">🏆 Standings</div>
            <ul className="text-sm text-base-dark">
              {standings.table?.map((t:any,i:number)=> (
                <li key={i} className="flex justify-between border-b py-1"><span>{t.team}</span><span className="text-gray-600">{t.record}</span></li>
              ))}
              {!standings.table?.length && <li className="text-xs text-gray-600">Standings unavailble. Connect ESPN to fetch.</li>}
            </ul>
            <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('standings')}>More</a></div>
          </div>
          {/* Injury timelines */}
          {cards.injuries?.map((n:any,i:number)=> (
            <div key={`inj-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">🩺 {n.player} {n.team? `(${n.team})`:''}</div>
              <div className="text-xs mb-1"><span className="badge bg-yellow-100 text-yellow-800">{n.tag}</span> <span className="muted">{new Date(n.timestamp).toLocaleString()}</span></div>
              <div className="text-sm text-base-dark">{n.note||'No details available.'}</div>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('injuries')}>More</a></div>
            </div>
          ))}
          {/* Bye week alerts */}
          {cards.byes?.map((b:any,i:number)=> (
            <div key={`bye-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">🛌 Bye Week Alert</div>
              <div className="text-sm text-base-dark">{b.player} ({b.team}) — {b.position} has a bye in Week {b.bye_week}.</div>
              {b.replacement && <div className="text-xs mt-1 text-muted-dark">Suggested replacement: <span className="font-medium">{b.replacement}</span></div>}
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('byes')}>More</a></div>
            </div>
          ))}
          {/* Weather warnings */}
          {cards.weather?.map((w:any,i:number)=> (
            <div key={`wx-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">🌧️ Weather Watch</div>
              <div className="text-sm text-base-dark">{w.player} ({w.team}) — {w.wx?.temp_c!=null ? `${Math.round((w.wx.temp_c*9/5)+32)}°F, `:''}{w.wx?.precip_prob!=null? `${w.wx.precip_prob}% rain, `:''}{w.wx?.wind_kmh!=null? `${w.wx.wind_kmh} km/h wind`:''}</div>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('weather')}>More</a></div>
            </div>
          ))}
          {/* Matchups */}
          {cards.matchups?.map((m:any,i:number)=> (
            <div key={`mx-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">📊 Matchup</div>
              <div className="text-sm text-base-dark">{m.player} ({m.team}) vs {m.opponent} — <span className="font-medium">{m.tag}</span> (rank {m.rank}{m.fp_allowed? `, ${m.fp_allowed} fpts allowed`:''})</div>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('matchups')}>More</a></div>
            </div>
          ))}
          {/* Late swap reminders */}
          {cards.late_swap?.map((s:any,i:number)=> (
            <div key={`ls-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">⏰ Late Swap</div>
              <div className="text-sm text-base-dark">{s.player} ({s.team}) — Kickoff {new Date(s.kickoff).toLocaleString()}</div>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('late_swap')}>More</a></div>
            </div>
          ))}
          {/* Waiver watchlist */}
          {cards.waivers?.map((w:any,i:number)=> (
            <div key={`wv-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">🛒 Waiver Watch</div>
              <div className="text-sm text-base-dark">{w.name} — {w.team} • VORP Δ {w.vorp_delta}</div>
              <div className="text-xs mt-1 text-muted-dark">Suggested FAAB: {w.faab}</div>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('waivers')}>More</a></div>
            </div>
          ))}
          {/* Trade pulse */}
          {cards.trade?.map((t:any,i:number)=> (
            <div key={`tr-${i}`} className="min-w-[260px] p-3 rounded bg-soft-dark border border-muted-dark">
              <div className="font-semibold mb-1">🔄 Trade Pulse</div>
              <div className="text-sm text-base-dark">{t.summary}</div>
              <div className="text-right mt-1"><a className="link" onClick={()=>openDetails('trade')}>More</a></div>
            </div>
          ))}
        </Carousel>
      </div>
      <DetailsModal cards={cards} standings={standings} news={news} />
    </div>
  )
}

function Carousel({children}:{children:any}){
  const items = useMemo(()=>React.Children.toArray(children),[children])
  const doubled = useMemo(()=>items.concat(items),[items])
  return (
    <div className="relative pb-2 carousel">
      <div className="carousel-track">
        {doubled}
      </div>
    </div>
  )
}

function DetailsModal({ cards, standings, news }:{ cards:any, standings:any, news:any }){
  const [open,setOpen]=useState(false)
  const [dtype,setType]=useState('')
  const [filter,setFilter]=useState('all')
  ;(window as any).__setDetailsOpen = setOpen
  ;(window as any).__setDetailsType = setType
  const items = useMemo(()=>{
    if (dtype==='news') return (news && (news.items||[]).filter((x:any)=>x.kind==='news')) || []
    const list = dtype==='standings' ? standings.table : (cards as any)[dtype] || []
    if (dtype==='injuries' && filter!=='all'){
      const f = filter.toLowerCase()
      return list.filter((n:any)=> ((n.tag||'').toLowerCase().includes(f) || (n.status||'').toLowerCase().includes(f)))
    }
    if (dtype==='byes' && filter!=='all') return list.filter((b:any)=> (b.position||'').toLowerCase()===filter)
    if (dtype==='matchups' && filter!=='all') return list.filter((m:any)=> filter==='easy' ? (m.tag||'').includes('Easy') : (m.tag||'').includes('Tough'))
    if (dtype==='weather' && filter!=='all') return list.filter((w:any)=> filter==='wind' ? (w.wx?.wind_kmh||0)>=25 : (w.wx?.precip_prob||0)>=60)
    return list
  },[dtype, filter, cards, standings, news])
  const FilterCtl = () => {
    if (dtype==='injuries') return (
      <select value={filter} onChange={e=>setFilter(e.target.value)} className="border p-1 text-sm">
        <option value="all">All</option>
        <option value="active">Active</option>
        <option value="questionable">Questionable</option>
        <option value="doubtful">Doubtful</option>
        <option value="out">Out</option>
        <option value="expected">Expected</option>
      </select>)
    if (dtype==='byes') return (
      <select value={filter} onChange={e=>setFilter(e.target.value)} className="border p-1 text-sm">
        <option value="all">All</option>
        {['qb','rb','wr','te','k','dst'].map(p=>(<option key={p} value={p}>{p.toUpperCase()}</option>))}
      </select>)
    if (dtype==='matchups') return (
      <select value={filter} onChange={e=>setFilter(e.target.value)} className="border p-1 text-sm">
        <option value="all">All</option>
        <option value="easy">Easy</option>
        <option value="tough">Tough</option>
      </select>)
    if (dtype==='weather') return (
      <select value={filter} onChange={e=>setFilter(e.target.value)} className="border p-1 text-sm">
        <option value="all">All</option>
        <option value="wind">Windy</option>
        <option value="rain">Rain</option>
      </select>)
    return null
  }
  return (
    <Modal open={open} title={dtype ? dtype.replace('_',' ').toUpperCase() : 'Details'}>
      <div className="flex items-center gap-2 mb-2">
        <FilterCtl />
        <button onClick={()=>setOpen(false)} className="ml-auto px-2 py-1 bg-gray-200 dark:bg-gray-700 rounded text-sm">Close</button>
      </div>
      <div className="space-y-2 max-h-80 overflow-auto">
        {dtype==='standings' && items.map((t:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{t.team}</div><div className="text-sm">{t.record} • PF {t.points_for}</div></div>
        ))}
        {(dtype==='injuries' || dtype==='news') && items.map((n:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{n.player || n.name} {n.team? `(${n.team})`:''} — {n.tag || n.status}</div><div className="text-xs muted">{n.timestamp? new Date(n.timestamp).toLocaleString(): ''}</div><div className="text-sm">{n.note||'No details.'}</div></div>
        ))}
        {dtype==='byes' && items.map((b:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{b.player} ({b.team}) — Week {b.bye_week}</div><div className="text-sm">Position: {b.position}{b.replacement? ` • Replacement: ${b.replacement}`:''}</div></div>
        ))}
        {dtype==='matchups' && items.map((m:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{m.player} vs {m.opponent}</div><div className="text-sm">{m.tag} — rank {m.rank}{m.fp_allowed? `, ${m.fp_allowed} fpts allowed`:''}</div></div>
        ))}
        {dtype==='weather' && items.map((w:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{w.player} ({w.team})</div><div className="text-sm">{w.wx?.temp_c!=null? `${Math.round((w.wx.temp_c*9/5)+32)}°F, `:''}{w.wx?.precip_prob!=null? `${w.wx.precip_prob}% rain, `:''}{w.wx?.wind_kmh!=null? `${w.wx.wind_kmh} km/h wind`:''}</div></div>
        ))}
        {dtype==='late_swap' && items.map((s:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{s.player} ({s.team})</div><div className="text-sm">Kickoff {new Date(s.kickoff).toLocaleString()}</div></div>
        ))}
        {dtype==='waivers' && items.map((w:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">{w.name} — {w.team}</div><div className="text-sm">VORP Δ {w.vorp_delta} • FAAB {w.faab}</div></div>
        ))}
        {dtype==='trade' && items.map((t:any,i:number)=> (
          <div key={i} className="p-2 border rounded"><div className="font-semibold">Trade Pulse</div><div className="text-sm">{t.summary}</div></div>
        ))}
      </div>
    </Modal>
  )
}

function openDetails(type:string){
  (window as any).__setDetailsType && (window as any).__setDetailsType(type)
  ;(window as any).__setDetailsOpen && (window as any).__setDetailsOpen(true)
}
