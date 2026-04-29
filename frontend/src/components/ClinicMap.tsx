import { Map, MapControls, MapMarker, MarkerContent, MarkerPopup } from "@/components/ui/map"

type Clinic = {
  id: string
  name: string
  address: string
  lng: number
  lat: number
}

const SAMPLE_CLINICS: Clinic[] = [
  { id: "1", name: "Appletree Medical Group", address: "180 Metcalfe St, Ottawa", lng: -75.6934, lat: 45.4200 },
  { id: "2", name: "Somerset West CHC", address: "55 Eccles St, Ottawa", lng: -75.7100, lat: 45.4145 },
  { id: "3", name: "Centretown CHC", address: "340 Gilmour St, Ottawa", lng: -75.6988, lat: 45.4157 },
  { id: "4", name: "Sandy Hill CHC", address: "221 Nelson St, Ottawa", lng: -75.6745, lat: 45.4250 },
]

export function ClinicMap() {
  return (
    <div className="h-[400px] w-full overflow-hidden rounded-xl border">
      <Map center={[-75.6972, 45.4215]} zoom={13}>
        <MapControls />
        {SAMPLE_CLINICS.map((clinic) => (
          <MapMarker key={clinic.id} longitude={clinic.lng} latitude={clinic.lat}>
            <MarkerContent />
            <MarkerPopup closeButton>
              <p className="font-medium text-sm">{clinic.name}</p>
              <p className="text-muted-foreground text-xs mt-0.5">{clinic.address}</p>
            </MarkerPopup>
          </MapMarker>
        ))}
      </Map>
    </div>
  )
}
