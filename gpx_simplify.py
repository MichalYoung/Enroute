#! /usr/bin/env python3
#
"""
Filter a GPX file to simplified.
(Command line tool, for route preparation)

"""

# Load modules from ./lib
import sys
import argparse
import gpxpy
import gpxpy.gpx
import json 

delta = 100

def getargs():
    """Return arguments as a NameSpace object"""
    parser = argparse.ArgumentParser("Simplify GPX files")
    parser.add_argument('infile',
        type=argparse.FileType(mode='r', encoding="utf-8", errors="replace"), 
        help="The GPX input file")
    parser.add_argument('outfile', 
        type=argparse.FileType(mode='w', encoding="utf-8"),
        help="Output to this file")
    parser.add_argument("--points", dest="format", action="store_const",
                            const="points", default="gpx",
                            help="Output as JSON list of points (default gpx)")
    parser.add_argument("--delta", dest="delta", type=int, default=100,
                            help="Max deviation from input route, in meters")
    argvals = parser.parse_args()
    return argvals

def points(gpx_obj):
    """
    Extract all the track points from a gpx object.
    Returns a list of points.
    """
    li = [ ] 
    for track in gpx_obj.tracks:
        for segment in track.segments:
            for point in segment.points:
                li.append([point.latitude, point.longitude])
    return li
                               
def main():
    args = getargs()
    gpx = gpxpy.parse(args.infile)
    delta = args.delta
    gpx.simplify(delta)
    if args.format == "points": 
        print(json.dumps(points(gpx)), file=args.outfile)
    else: 
        print(gpx.to_xml(), file=args.outfile)

main()




