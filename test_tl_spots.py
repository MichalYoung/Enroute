"""
Check rented spots for  connections. Gives  a list of all live spots,
with assigned rider.
"""

import trackleaders
import device_assignments
import arrow

assignments = device_assignments.read_assignments("SPOT_assignments.xlsx")
rider_by_esn = { }
unit_by_esn = { }
esns = [ ]
for tl_spot in assignments["trackleaders_spots"]:
    esn = tl_spot["esn"]
    rider = tl_spot["rider"]
    unit = tl_spot["unit"]
    rider_by_esn[esn] = rider
    unit_by_esn[esn] = unit
    esns.append(esn)
tracks = trackleaders.get_tracks(esns)

for track in tracks:
    esn = track["id"]
    track["rider"] = rider_by_esn[esn]
    track["observed"] = arrow.get(track["latest"]["dateTime"]).to("local")
    track["unit"] = unit_by_esn[esn]

tracks = sorted(tracks, key=lambda track: track["unit"])
recent = arrow.now().replace(days=-1)
for track in tracks:
    if track["observed"] < recent:
        recency = "STALE"
    else:
        recency = "FRESH"
    print(f'{recency}  --- {track["unit"]} --- {track["rider"]}')


