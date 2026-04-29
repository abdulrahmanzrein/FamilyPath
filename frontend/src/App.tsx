import { useState } from 'react'
import { Map, MapMarker, MarkerContent, MarkerPopup } from '@/components/ui/map'

type Page = 'home' | 'find'
type Availability = 'available' | 'unavailable' | 'unknown'

const MARKER_COLOR: Record<Availability, string> = {
  available:   'bg-green-500',
  unavailable: 'bg-red-500',
  unknown:     'bg-amber-500',
}

const MARKER_LABEL: Record<Availability, string> = {
  available:   'Taking new patients',
  unavailable: 'Not taking patients',
  unknown:     'Need to call to check',
}

const CLINICS = [
  { id: '1', name: 'Grand River Medical', address: '835 King St W, Kitchener', lng: -80.4927, lat: 43.4516, availability: 'available' as Availability },
  { id: '2', name: 'Waterloo Family Health', address: '180 King St S, Waterloo', lng: -80.5200, lat: 43.4650, availability: 'unknown' as Availability },
  { id: '3', name: 'Uptown Medical Centre', address: '75 King St N, Waterloo', lng: -80.5180, lat: 43.4744, availability: 'unknown' as Availability },
  { id: '4', name: 'Cambridge Health Centre', address: '700 Coronation Blvd, Cambridge', lng: -80.3123, lat: 43.3601, availability: 'unavailable' as Availability },
]

function App() {
  const [page, setPage] = useState<Page>('home')
  const [name, setName] = useState('')
  const [postal, setPostal] = useState('')
  const [language, setLanguage] = useState('')

  return (
    <div className="flex flex-col h-screen">

      {/* Header */}
      <header className="flex items-center justify-between px-8 py-4 border-b bg-white">
        <h1 className="text-xl font-bold text-blue-600">FamilyPath</h1>
        <nav className="flex gap-6">
          <button onClick={() => setPage('home')} className={`text-sm font-medium ${page === 'home' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'}`}>Home</button>
          <button onClick={() => setPage('find')} className={`text-sm font-medium ${page === 'find' ? 'text-blue-600' : 'text-gray-500 hover:text-gray-900'}`}>Find a Family Doctor</button>
        </nav>
      </header>

   
      

      {/* Home page */}
      {page === 'home' && (
        <div className="flex-1 flex flex-col items-center justify-center gap-4 px-8">
          <h2 className="text-4xl font-bold text-gray-900">Find a family doctor in your area</h2>
          <p className="text-gray-500 text-sm">Connecting you with doctors who speak your language and are accepting new patients.</p>
          <button onClick={() => setPage('find')} className="mt-2 bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700">Search your family doctor</button>

          <div className="mt-10 w-full max-w-3xl">
            <h3 className="text-lg font-semibold text-gray-900 text-center mb-6">How it works</h3>
            <div className="relative grid grid-cols-4 gap-6">
              <div className="absolute top-5 left-[12.5%] right-[12.5%] h-0.5 bg-blue-200" />
              {[
                { n: 1, title: 'Enter your info', desc: 'Tell us your name, postal code, and preferred language.' },
                { n: 2, title: 'We search for you', desc: 'Our agents scan multiple sources to find family doctors near you.' },
                { n: 3, title: 'We call to confirm', desc: 'We call clinics on your behalf to confirm they are accepting new patients.' },
                { n: 4, title: 'Get your results', desc: 'View confirmed doctors on the map and choose the right one for you.' },
              ].map(s => (
                <div key={s.n} className="flex flex-col items-center text-center gap-2 relative">
                  <div className="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold z-10">{s.n}</div>
                  <p className="font-medium text-sm text-gray-900">{s.title}</p>
                  <p className="text-xs text-gray-500">{s.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Find page */}
      {page === 'find' && (
        <div className="flex flex-1">

          <div className="w-2/5 bg-blue-600 flex flex-col p-8 gap-6">
            <div>
              <h2 className="text-2xl font-bold text-white">Find a Family Doctor</h2>
              <p className="text-blue-100 text-sm mt-1">Find a doctor who speaks your language</p>
            </div>

            <div className="bg-white rounded-2xl p-6 flex flex-col gap-4">
              <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} />
              <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Postal Code" value={postal} onChange={e => setPostal(e.target.value)} />
              <select className="border rounded-lg px-3 py-2 text-sm bg-white" value={language} onChange={e => setLanguage(e.target.value)}>
                <option value="">Select a language</option>
                <option value="punjabi">Punjabi</option>
                <option value="arabic">Arabic</option>
                <option value="tagalog">Tagalog</option>
                <option value="spanish">Spanish</option>
                <option value="english">English</option>
                <option value="french">French</option>
                <option value="hindi">Hindi</option>
              </select>
              <button className="bg-blue-600 text-white rounded-lg py-2 text-sm font-medium">Find Doctors</button>
            </div>
          </div>

          <div className="flex-1">
            <Map center={[-80.4927, 43.4516]} zoom={12} theme="light">
              {CLINICS.map(c => (
                <MapMarker key={c.id} longitude={c.lng} latitude={c.lat}>
                  <MarkerContent>
                    <div className={`${MARKER_COLOR[c.availability]} w-4 h-4 rounded-full border-2 border-white shadow-md`} />
                  </MarkerContent>
                  <MarkerPopup closeButton>
                    <p className="font-semibold text-sm">{c.name}</p>
                    <p className="text-xs text-gray-500">{c.address}</p>
                    <p className={`text-xs mt-1 font-medium ${MARKER_COLOR[c.availability].replace('bg-', 'text-')}`}>{MARKER_LABEL[c.availability]}</p>
                  </MarkerPopup>
                </MapMarker>
              ))}
            </Map>
          </div>

        </div>
      )}

    </div>
  )
}

export default App
