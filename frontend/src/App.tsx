import { useState } from 'react'
import { Map, MapMarker, MarkerContent, MarkerPopup, MapControls } from '@/components/ui/map'
import { Button } from '@/components/ui/button'
import { AgentGrid } from '@/components/AgentGrid'
import type { AgentSource, AgentStatus } from '@/hooks/useSearchWebSocket'
import { useSearchWebSocket } from '@/hooks/useSearchWebSocket'
import { startSearch } from '@/api/client'
import { Heart, MapPin, Search, PhoneCall, ClipboardList, ShieldCheck, Stethoscope, ArrowRight, CheckCircle2, Phone, Globe2, Lock, Sparkles, Loader2 } from 'lucide-react'

type Page = 'home' | 'find'

// Demo clinic pins for the map — Brampton / Scarborough per PRD data sources
const DEMO_CLINICS = [
  { id: '1', name: 'Heart Lake Health Centre',        address: '55 Quarry Edge Dr, Brampton',  lng: -79.8021, lat: 43.7530 },
  { id: '2', name: 'Bramalea Community Clinic',        address: '150 Central Park Dr, Brampton', lng: -79.7050, lat: 43.7100 },
  { id: '3', name: 'Sandalwood Medical Clinic',        address: '475 Sandalwood Pkwy E, Brampton', lng: -79.7823, lat: 43.7489 },
  { id: '4', name: 'Scarborough Newcomer Health Centre', address: '2425 Eglinton Ave E, Scarborough', lng: -79.2620, lat: 43.7597 },
]

function App() {
  const [page, setPage] = useState<Page>('home')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [postal, setPostal] = useState('')
  const [language, setLanguage] = useState('')
  const [insurance, setInsurance] = useState('')
  const [searchId, setSearchId] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const { agents, connected } = useSearchWebSocket(searchId)

  // Build a map keyed by source for the AgentGrid
  const agentMap = agents.reduce<Partial<Record<AgentSource, AgentStatus>>>((acc, a) => {
    acc[a.source] = a
    return acc
  }, {})

  async function handleSearch() {
    if (!name.trim() || !postal.trim() || !language || !insurance) return
    const insuranceValue = insurance === 'waiting' ? 'waiting_period' : insurance as 'ohip' | 'ifhp' | 'uhip' | 'waiting_period'
    setSearching(true)
    setError(null)
    try {
      const res = await startSearch({
        name: name.trim(),
        phone: phone.trim(),
        postal_code: postal.trim(),
        language,
        insurance_type: insuranceValue,
      })
      setSearchId(res.search_id)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Search failed — is the backend running?')
    } finally {
      setSearching(false)
    }
  }

  const searched = searchId !== null

  return (
    <div className="flex flex-col h-screen bg-slate-50 antialiased">
      <header className="flex items-center justify-between px-6 md:px-10 py-4 bg-white/95 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50">
        <Button variant="ghost" onClick={() => setPage('home')} className="group h-auto px-2 py-1 gap-2.5 hover:bg-transparent">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center shadow-sm shadow-blue-600/20 group-hover:shadow-blue-600/40 group-hover:scale-105 transition-all duration-200">
            <Heart className="w-4.5 h-4.5 text-white" fill="currentColor" />
          </div>
          <span className="text-lg font-bold text-slate-900 tracking-tight">MedBridge</span>
        </Button>
        <nav className="flex items-center gap-1">
          <Button variant="ghost" onClick={() => setPage('home')} className={`h-auto text-sm font-medium px-4 py-2 rounded-lg transition-all duration-200 ${page === 'home' ? 'text-blue-700 bg-blue-50 hover:bg-blue-50 hover:text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}>Home</Button>
          <Button variant="ghost" onClick={() => setPage('find')} className={`h-auto text-sm font-medium px-4 py-2 rounded-lg transition-all duration-200 ${page === 'find' ? 'text-blue-700 bg-blue-50 hover:bg-blue-50 hover:text-blue-700' : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'}`}>Find a Doctor</Button>
          <Button onClick={() => setPage('find')} className="ml-3 hidden md:inline-flex items-center gap-1.5 h-auto text-sm font-semibold bg-slate-900 text-white px-4 py-2 rounded-lg hover:bg-slate-800 active:bg-black transition-all duration-200 shadow-sm">
            Get started
            <ArrowRight className="w-3.5 h-3.5" />
          </Button>
        </nav>
      </header>

      {page === 'home' && (
        <div className="flex-1 overflow-y-auto bg-white">
          <section className="relative overflow-hidden bg-gradient-to-b from-blue-50/60 via-white to-white">
            <div className="absolute inset-0 -z-0" style={{ backgroundImage: 'radial-gradient(circle at 1px 1px, rgb(15 23 42 / 0.06) 1px, transparent 0)', backgroundSize: '32px 32px' }} />
            <div className="absolute -top-24 -right-24 w-96 h-96 rounded-full bg-blue-200/40 blur-3xl -z-0" />
            <div className="absolute -bottom-32 -left-24 w-96 h-96 rounded-full bg-emerald-200/30 blur-3xl -z-0" />
            <div className="relative max-w-6xl mx-auto px-6 md:px-10 pt-16 md:pt-24 pb-20 md:pb-28 flex flex-col items-center text-center gap-6">
              <div className="inline-flex items-center gap-2 bg-white border border-slate-200 px-3.5 py-1.5 rounded-full text-xs font-medium text-slate-700 shadow-sm">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
                </span>
                Now serving newcomers across Brampton & Scarborough
              </div>
              <h1 className="text-4xl md:text-6xl font-bold tracking-tight text-slate-900 max-w-4xl leading-[1.05]">
                Find a family doctor
                <span className="block bg-gradient-to-r from-blue-600 to-blue-800 bg-clip-text text-transparent">who speaks your language.</span>
              </h1>
              <p className="text-slate-600 text-base md:text-lg max-w-2xl leading-relaxed">
                We connect newcomers with family doctors across Ontario who are accepting new patients — for free, in your preferred language.
              </p>
              <div className="flex flex-col sm:flex-row items-center gap-3 mt-2">
                <Button onClick={() => setPage('find')} className="group bg-blue-700 text-white px-6 py-3.5 h-auto rounded-xl text-sm font-semibold hover:bg-blue-800 active:bg-blue-900 transition-all duration-200 shadow-lg shadow-blue-700/20 hover:shadow-blue-700/40 hover:-translate-y-0.5 inline-flex items-center gap-2">
                  <Search className="w-4 h-4" />
                  Search your family doctor
                  <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
                </Button>
                <Button variant="ghost" className="px-6 py-3.5 h-auto rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-100 active:bg-slate-200 transition-all duration-200 inline-flex items-center gap-2">
                  <Phone className="w-4 h-4" />
                  Talk to a navigator
                </Button>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-x-6 gap-y-2 mt-3 text-xs text-slate-500">
                <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />100% free service</span>
                <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />No OHIP card required</span>
                <span className="inline-flex items-center gap-1.5"><CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />Multilingual support</span>
              </div>
            </div>
          </section>

          <section className="border-y border-slate-200 bg-slate-50/50">
            <div className="max-w-6xl mx-auto px-6 md:px-10 py-10 grid grid-cols-2 md:grid-cols-4 gap-6 md:gap-8">
              {[
                { stat: '10+', label: 'Verified clinics' },
                { stat: '4', label: 'Languages supported' },
                { stat: '< 5 min', label: 'Average search time' },
                { stat: '100%', label: 'Free for patients' },
              ].map(s => (
                <div key={s.label} className="text-center md:text-left">
                  <p className="text-2xl md:text-3xl font-bold tracking-tight text-slate-900">{s.stat}</p>
                  <p className="text-xs md:text-sm text-slate-500 mt-1">{s.label}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="max-w-6xl mx-auto px-6 md:px-10 py-20 md:py-24">
            <div className="text-center mb-14 md:mb-16 max-w-2xl mx-auto">
              <p className="text-xs font-semibold text-blue-700 uppercase tracking-[0.15em] mb-3">How it works</p>
              <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900">Four steps to your new family doctor</h2>
              <p className="text-slate-600 text-base mt-4 leading-relaxed">From intake to confirmed appointment — we handle the calls, paperwork, and follow-ups so you don't have to.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
              {[
                { n: 1, icon: ClipboardList, title: 'Tell us about you', desc: 'Share your name, postal code, and preferred language. Takes under a minute.' },
                { n: 2, icon: Search, title: 'We search for you', desc: 'Our agents scan official Ontario registries to find family doctors near you.' },
                { n: 3, icon: PhoneCall, title: 'We call to confirm', desc: 'We phone clinics directly to verify they are accepting new patients today.' },
                { n: 4, icon: MapPin, title: 'See your matches', desc: 'View confirmed doctors on a map and pick the one that works for you.' },
              ].map(s => {
                const Icon = s.icon
                return (
                  <div key={s.n} className="group relative bg-white border border-slate-200 rounded-2xl p-6 hover:border-blue-300 hover:shadow-lg hover:shadow-blue-700/5 hover:-translate-y-1 transition-all duration-300">
                    <div className="absolute top-5 right-5 text-5xl font-bold text-slate-100 group-hover:text-blue-100 transition-colors duration-300 leading-none select-none">{s.n}</div>
                    <div className="relative w-11 h-11 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center mb-5 group-hover:bg-blue-700 group-hover:border-blue-700 transition-all duration-300">
                      <Icon className="w-5 h-5 text-blue-700 group-hover:text-white transition-colors duration-300" />
                    </div>
                    <p className="font-semibold text-slate-900 text-base mb-2">{s.title}</p>
                    <p className="text-sm text-slate-600 leading-relaxed">{s.desc}</p>
                  </div>
                )
              })}
            </div>
          </section>

          <section className="bg-gradient-to-b from-white to-slate-50 border-t border-slate-200">
            <div className="max-w-6xl mx-auto px-6 md:px-10 py-20 md:py-24">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-center">
                <div>
                  <p className="text-xs font-semibold text-blue-700 uppercase tracking-[0.15em] mb-3">Why MedBridge</p>
                  <h2 className="text-3xl md:text-4xl font-bold tracking-tight text-slate-900 leading-tight">Built for newcomers, trusted by Ontarians.</h2>
                  <p className="text-slate-600 text-base mt-4 leading-relaxed">Finding a family doctor in Ontario is hard. We make it simple, multilingual, and fully free — no OHIP card required to get started.</p>
                </div>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {[
                    { icon: ShieldCheck, title: 'Privacy first', desc: 'Your information is never shared without consent.', color: 'blue' },
                    { icon: Stethoscope, title: 'Verified clinics', desc: 'Sourced directly from official Ontario registries.', color: 'emerald' },
                    { icon: Globe2, title: 'Multilingual', desc: 'Punjabi, Arabic, Tagalog, Spanish, and more.', color: 'amber' },
                    { icon: Lock, title: 'Secure by design', desc: 'Bank-level encryption protects your data.', color: 'violet' },
                  ].map((f, i) => {
                    const Icon = f.icon
                    const colors: Record<string, string> = {
                      blue: 'bg-blue-50 text-blue-700 border-blue-100',
                      emerald: 'bg-emerald-50 text-emerald-700 border-emerald-100',
                      amber: 'bg-amber-50 text-amber-700 border-amber-100',
                      violet: 'bg-violet-50 text-violet-700 border-violet-100',
                    }
                    return (
                      <div key={i} className="bg-white rounded-xl p-5 border border-slate-200 hover:border-slate-300 hover:shadow-sm transition-all duration-200">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center border ${colors[f.color]} mb-3`}>
                          <Icon className="w-5 h-5" />
                        </div>
                        <p className="font-semibold text-slate-900 text-sm">{f.title}</p>
                        <p className="text-xs text-slate-600 mt-1 leading-relaxed">{f.desc}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          </section>

          <section className="bg-slate-900 text-white">
            <div className="max-w-5xl mx-auto px-6 md:px-10 py-16 md:py-20 flex flex-col items-center text-center gap-6">
              <div className="inline-flex items-center gap-2 bg-white/10 border border-white/20 px-3 py-1 rounded-full text-xs font-medium text-white">
                <Sparkles className="w-3.5 h-3.5" />
                Ready when you are
              </div>
              <h2 className="text-3xl md:text-5xl font-bold tracking-tight max-w-3xl leading-tight">Start your search in under a minute.</h2>
              <p className="text-slate-300 text-base max-w-xl leading-relaxed">No forms to download. No waiting rooms. Just a clear path to a family doctor who fits your needs.</p>
              <Button onClick={() => setPage('find')} className="group bg-white text-slate-900 px-6 py-3.5 h-auto rounded-xl text-sm font-semibold hover:bg-slate-100 active:bg-slate-200 transition-all duration-200 shadow-lg hover:-translate-y-0.5 inline-flex items-center gap-2 mt-2">
                Find a doctor now
                <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
              </Button>
            </div>
          </section>

          <footer className="border-t border-slate-200 bg-white">
            <div className="max-w-6xl mx-auto px-6 md:px-10 py-8 flex flex-col md:flex-row items-center justify-between gap-3 text-xs text-slate-500">
              <div className="flex items-center gap-2">
                <div className="w-6 h-6 rounded-md bg-gradient-to-br from-blue-600 to-blue-800 flex items-center justify-center">
                  <Heart className="w-3 h-3 text-white" fill="currentColor" />
                </div>
                <p>&copy; 2026 MedBridge. Healthcare navigation for everyone.</p>
              </div>
              <p className="text-slate-400">Built for ConHacks 2026</p>
            </div>
          </footer>
        </div>
      )}

      {page === 'find' && (
        <div className="flex flex-1 overflow-hidden bg-slate-50">
          <aside className="w-full md:w-[440px] lg:w-[480px] bg-white border-r border-slate-200 flex flex-col overflow-y-auto">
            <div className="px-7 pt-7 pb-5 border-b border-slate-100">
              <div className="inline-flex items-center gap-1.5 bg-blue-50 border border-blue-100 px-2.5 py-1 rounded-full text-[11px] font-semibold text-blue-700 uppercase tracking-wider mb-4">
                <Stethoscope className="w-3 h-3" />
                Patient intake
              </div>
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Find a family doctor</h2>
              <p className="text-slate-600 text-sm mt-1.5 leading-relaxed">Tell us a bit about yourself and we'll find a doctor who speaks your language.</p>
            </div>
            <div className="px-7 py-6 flex flex-col gap-5">
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Full name</label>
                <input className="border border-slate-200 rounded-lg px-3.5 py-3 text-sm bg-white placeholder:text-slate-400 focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition-all duration-200" placeholder="Jane Doe" value={name} onChange={e => setName(e.target.value)} />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Phone number</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  <input className="w-full border border-slate-200 rounded-lg pl-9 pr-3.5 py-3 text-sm bg-white placeholder:text-slate-400 focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition-all duration-200" placeholder="+1 (416) 555-0100" value={phone} onChange={e => setPhone(e.target.value)} />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Postal code</label>
                <div className="relative">
                  <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                  <input className="w-full border border-slate-200 rounded-lg pl-9 pr-3.5 py-3 text-sm bg-white placeholder:text-slate-400 focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition-all duration-200" placeholder="L6V 4K2" value={postal} onChange={e => setPostal(e.target.value)} />
                </div>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Preferred language</label>
                <select className="border border-slate-200 rounded-lg px-3.5 py-3 text-sm bg-white text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition-all duration-200" value={language} onChange={e => setLanguage(e.target.value)}>
                  <option value="">Select a language</option>
                  <option value="punjabi">Punjabi</option>
                  <option value="arabic">Arabic</option>
                  <option value="tagalog">Tagalog</option>
                  <option value="spanish">Spanish</option>
                  <option value="english">English</option>
                  <option value="french">French</option>
                  <option value="hindi">Hindi</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-semibold text-slate-700">Insurance type</label>
                <select className="border border-slate-200 rounded-lg px-3.5 py-3 text-sm bg-white text-slate-900 focus:outline-none focus:border-blue-600 focus:ring-4 focus:ring-blue-100 transition-all duration-200" value={insurance} onChange={e => setInsurance(e.target.value)}>
                  <option value="">Select insurance</option>
                  <option value="ohip">OHIP</option>
                  <option value="ifhp">IFHP (Refugee Health)</option>
                  <option value="uhip">UHIP (International Student)</option>
                  <option value="waiting">Waiting Period (No coverage yet)</option>
                </select>
              </div>
              {error && (
                <p className="text-xs text-rose-600 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{error}</p>
              )}
              <Button
                onClick={handleSearch}
                disabled={searching || !name.trim() || !postal.trim() || !language || !insurance}
                className="group bg-blue-700 text-white rounded-lg py-3 h-auto text-sm font-semibold hover:bg-blue-800 active:bg-blue-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 inline-flex items-center justify-center gap-2 shadow-sm shadow-blue-700/20 hover:shadow-blue-700/40 mt-1"
              >
                {searching ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                {searching ? 'Starting search…' : 'Find doctors'}
                {!searching && <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />}
              </Button>
              <p className="inline-flex items-center justify-center gap-1.5 text-xs text-slate-500 leading-relaxed">
                <Lock className="w-3 h-3" />
                Your information stays private and encrypted.
              </p>
            </div>

            {searched && (
              <div className="border-t border-slate-100 bg-slate-50/50 px-7 py-6 flex flex-col gap-3">
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-sm font-bold text-slate-900">Agent status</h3>
                  <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${connected ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-amber-50 text-amber-700 border-amber-200'}`}>
                    {connected ? 'Live' : 'Connecting…'}
                  </span>
                </div>
                <AgentGrid agentMap={agentMap} />

                {/* Confirmed match list */}
                {agents.some(a => a.status === 'confirmed') && (
                  <div className="mt-2 flex flex-col gap-2.5">
                    <h3 className="text-sm font-bold text-slate-900">Confirmed matches</h3>
                    {agents.filter(a => a.status === 'confirmed').map(a => (
                      <div key={a.source} className="bg-white rounded-xl p-4 border border-emerald-300 shadow-sm">
                        <div className="flex items-start gap-3">
                          <div className="shrink-0 w-10 h-10 rounded-lg bg-emerald-50 border border-emerald-200 flex items-center justify-center">
                            <Stethoscope className="w-4 h-4 text-emerald-700" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-semibold text-slate-900 text-sm leading-tight">{a.clinic_name}</p>
                            <p className="text-xs text-slate-500 mt-1">{a.message}</p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="mt-auto px-7 py-5 border-t border-slate-200 bg-blue-50/50">
              <div className="flex items-start gap-3">
                <div className="shrink-0 w-9 h-9 rounded-lg bg-blue-700 flex items-center justify-center shadow-sm">
                  <Phone className="w-4 h-4 text-white" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Need urgent care?</p>
                  <p className="text-xs text-slate-600 mt-0.5 leading-relaxed">Call Telehealth Ontario at <span className="font-bold text-blue-700">811</span> for free 24/7 health advice.</p>
                </div>
              </div>
            </div>
          </aside>

          <div className="flex-1 relative">
            {/* Map centred on Brampton */}
            <Map center={[-79.7609, 43.7315]} zoom={11} theme="light">
              <MapControls />
              {searched && DEMO_CLINICS.map(c => (
                <MapMarker key={c.id} longitude={c.lng} latitude={c.lat}>
                  <MarkerContent>
                    <div className="bg-emerald-500 w-4 h-4 rounded-full border-2 border-white shadow-md" />
                  </MarkerContent>
                  <MarkerPopup closeButton>
                    <p className="font-semibold text-sm">{c.name}</p>
                    <p className="text-xs text-gray-500">{c.address}</p>
                  </MarkerPopup>
                </MapMarker>
              ))}
            </Map>
            {!searched && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none p-4">
                <div className="bg-white border border-slate-200 rounded-2xl shadow-xl shadow-slate-900/10 px-8 py-7 max-w-sm flex flex-col items-center text-center gap-4">
                  <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 flex items-center justify-center">
                    <MapPin className="w-6 h-6 text-blue-700" />
                  </div>
                  <div>
                    <p className="text-base font-bold text-slate-900 leading-snug">No clinics to show yet</p>
                    <p className="text-sm text-slate-600 leading-relaxed mt-1.5">Fill out the form and tap <span className="font-semibold text-blue-700">Find doctors</span> to see clinics near you.</p>
                  </div>
                </div>
              </div>
            )}
            {searched && (
              <div className="absolute top-4 right-4 bg-white rounded-xl shadow-lg shadow-slate-900/5 border border-slate-200 p-4 w-64">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-xs font-bold text-slate-900 uppercase tracking-wider">Clinic status</p>
                  <span className="text-[10px] font-medium text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">Legend</span>
                </div>
                <div className="flex flex-col gap-2">
                  <div className="flex items-center gap-3">
                    <div className="bg-emerald-500 w-3 h-3 rounded-full border-2 border-white shadow ring-1 ring-slate-200 shrink-0" />
                    <span className="text-xs text-slate-700 font-medium">Confirmed match</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="bg-amber-400 w-3 h-3 rounded-full border-2 border-white shadow ring-1 ring-slate-200 shrink-0" />
                    <span className="text-xs text-slate-700 font-medium">Call in progress</span>
                  </div>
                </div>
                <div className="mt-3 pt-3 border-t border-slate-100">
                  <p className="text-[11px] text-slate-500 leading-relaxed">Showing {DEMO_CLINICS.length} clinics in Brampton / Scarborough. Click a marker for details.</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
