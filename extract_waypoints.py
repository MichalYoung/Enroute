"""
Extract from GPX file waypoints matching some string (case-insensitive).

usage: python3 extract_waypoints.py "summit" routes/mountains.gpx

Note: If a desired feature (e.g., summits) are cues but not waypoints in
a RWGPS route, use the "Include cues as waypoints" option under GPX track
export.   If you are processing with gpx_simplify.py anyway, there is
essentially no extra cost in initially dumping the GPX with extra waypoints.
"""

import gpxpy
import gpxpy.parser 
import sys

USAGE = 'usage: python3 extract_waypoints.py "summit" routes/mountains.gpx'

if len(sys.argv) != 3:
    print(USAGE)
    exit(1)

pattern = sys.argv[1].lower()
path = sys.argv[2]

gpx_file = open( path, 'r' )
parser = gpxpy.parser.GPXParser( gpx_file )
gpx = parser.parse()
gpx_file.close()

for waypoint in gpx.waypoints:
    desc = waypoint.comment or waypoint.description or "No description"
    if (pattern in waypoint.name.lower() or
        pattern in desc.lower()):
        print("{},{}  '{}' '{}'".format(
            waypoint.latitude, waypoint.longitude,
            waypoint.name, desc))
