import { useState } from 'react'
import { Map, MapMarker, MarkerContent, MarkerPopup } from '@/components/ui/map'

const CLINICS = [
  { id: '1', name: 'Grand River Medical', address: '835 King St W, Kitchener', lng: -80.4927, lat: 43.4516 },
  { id: '2', name: 'Waterloo Family Health', address: '180 King St S, Waterloo', lng: -80.5200, lat: 43.4650 },
  { id: '3', name: 'Uptown Medical Centre', address: '75 King St N, Waterloo', lng: -80.5180, lat: 43.4744 },
  { id: '4', name: 'Cambridge Health Centre', address: '700 Coronation Blvd, Cambridge', lng: -80.3123, lat: 43.3601 },
]

function App() {
  const [name, setName] = useState('')
  const [postal, setPostal] = useState('')
  const [language, setLanguage] = useState('')

  return (
    <div className="flex h-screen">

      <div className="w-2/5 bg-blue-600 flex flex-col p-8 gap-6">
        <h1 className="text-3xl font-bold text-white">FamilyPath</h1>
        <p className="text-blue-100 text-sm">Find a family doctor who speaks your language</p>

        <div className="bg-white rounded-2xl p-6 flex flex-col gap-4">
          <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Full Name" value={name} onChange={e => setName(e.target.value)} />
          <input className="border rounded-lg px-3 py-2 text-sm" placeholder="Postal Code" value={postal} onChange={e => setPostal(e.target.value)} />
          <select className="border rounded-lg px-3 py-2 text-sm bg-white" value={language} onChange={e => setLanguage(e.target.value)}>
            <option value="">Select a language</option>
            <option value="punjabi">Punjabi</option>
            <option value="arabic">Arabic</option>
            <option value="tagalog">Tagalog</option>
            <option value="spanish">Spanish</option>
          </select>
          <button className="bg-blue-600 text-white rounded-lg py-2 text-sm font-medium">Find Doctors</button>
        </div>
      </div>

      <div className="flex-1">
        <Map center={[-80.4927, 43.4516]} zoom={12}>
          {CLINICS.map(c => (
            <MapMarker key={c.id} longitude={c.lng} latitude={c.lat}>
              <MarkerContent />
              <MarkerPopup closeButton>
                <p className="font-semibold text-sm">{c.name}</p>
                <p className="text-xs text-gray-500">{c.address}</p>
              </MarkerPopup>
            </MapMarker>
          ))}
        </Map>
      </div>

    </div>
  )
}

export default App
