"""
Measure distances along a path represented as lat-lon pairs. 
(Experimental August 2017)
"""

import geopy.distance
import utm
import math
import json

import argparse

import logging
logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=logging.INFO)
log = logging.getLogger(__name__)

def dist_km( p1, p2 ):
    """Distance in kilometers between p1=(lat1, lon1) and p2=(lat2, lon2). 
    Usually measured with up to 20 iterations of Vincenty (ellipsoid) measure;
    may fall back to great circle method if geopy implementation of Vincenty
    fails to converge. 
    """
    try:
        dist = geopy.distance.vincenty( p1, p2 )
    except ValueError as e: 
        log.warning("Vincenty failed to converge on {}-{}; "
                      + " resorting to great circle"
                        .format(p1, p2))
        dist = geopy.great_circle( p1, p2 )
    return dist.kilometers

def utm_dist(p1, p2):
    """Distance calculated from UTM easting and northing; 
    should be close to dist_km. 
    """
    p1_lat, p1_lon = p1
    p2_lat, p2_lon = p2
    p1_east, p1_north, p1_zone, p1_code = utm.from_latlon(p1_lat, p1_lon)
    p2_east, p2_north, p2_zone, p2_code  = utm.from_latlon(p2_lat, p2_lon)
    if p1_zone != p2_zone:
        print("Zone difference, {} vs {}; forcing zone {}"
                        .format(p1_zone, p2_zone, p1_zone))
        p2_east, p2_north, _, _  = utm.from_latlon(p2_lat, p2_lon,
                                            force_zone_number=p1_zone)
    de = p2_east - p1_east
    dn = p2_north - p1_north
    dist_meters = math.sqrt( de*de + dn*dn )
    dist_kilometers = dist_meters / 1000.0
    return dist_kilometers


def utm_error( p1, p2 ):
    d_utm = utm_dist(p1, p2)
    d_vnc = dist_km(p1, p2)
    err = abs(d_utm - d_vnc)
    return err
    
def check_dist_pairs( path ):
    """Are my distance measurements with UTM close?"""
    if len(path) < 2:
        return
    prev = path[0]
    for pt in path[1:]:
        err = utm_error(prev, pt)
        print("{:4F}-{:4F} {:4F} {:4F}  DIFF: {:4F}"
                  .format(prev, pt, d_utm, d_vnc, err))
        prev = pt

    

def total_dist_km( path ):
    """Aggregate distance over a list of points"""
    tot_km = 0.0
    if len(path) < 2:
        return tot_km
    prev = path[0]
    for pt in path[1:]:
        seg_dist_km = dist_km(pt, prev)
        log.debug("dist {:4F} - {:4F} => {:4F}".format(prev, pt, seg_dist_km))
        tot_km += seg_dist_km
        prev = pt
    return tot_km

def track_centerpoint(track):
    """Given track == [[lat, lon], [lat, lon], ... ], 
    return (midlat, midlon) as central values, i.e., 
    midlat is halfway between min and max of lat, and midlon is 
    halfway between min and max of lon.
    """
    if len(track) == 0:
        return (0, 0)
    elif len(track) == 1:
        return track[0]
    min_lat, min_lon = track[0]
    max_lat, max_lon = track[0]
    for pt in track:
        lat, lon = pt
        if lat < min_lat:
            min_lat = lat
        if lat > max_lat:
            max_lat = lat
        if lon < min_lon:
            min_lon = lon
        if lon > max_lon:
            max_lon = lon
    return (min_lat + max_lat)/2.0, (min_lon + max_lon)/2.0

def track_to_utm(track):
    """convert [[lat, lon], [lat, lon], ... ]
    to [(easting, northing, cumdist), (easting, northing, cumdist), ...]
    with a zone --- we choose one UTM zone and make sure all eastings and 
    northings are in that zone, so that distance between points can be 
    computed directly from UTM values.
    """
    if len(track) == 0:
        return track, 10 

    # Determine UTM zone from center of path
    mid_lat, mid_lon = track_centerpoint(track)
    _, _, utm_zone, _ = utm.from_latlon(mid_lat, mid_lon)

    tot_km = 0 
    utm_path = [ ]
    prev = track[0]

    for pt in track:
        lat, lon = pt
        easting, northing, _, _ = \
          utm.from_latlon(lat, lon, force_zone_number=utm_zone)
        seg_dist_km = dist_km(prev, pt)
        tot_km += seg_dist_km
        utm_pt = (easting, northing, tot_km)
        utm_path.append(utm_pt)
        prev = pt

    return utm_path, utm_zone

def normal_intersect( seg_p1, seg_p2, p):
    """
    Find the point at which a line through seg_p1, 
    seg_p2 intersects a normal dropped from p. 
    """
    p1_x, p1_y = seg_p1
    p2_x, p2_y = seg_p2
    px, py = p

    # Special cases: slope or normal slope is undefined
    # for vertical or horizontal lines, but the intersections
    # are trivial for those cases
    if p2_x == p1_x:
        return p1_x, py
    elif p2_y == p1_y:
        return px, p1_y

    # The slope of the segment, and of a normal ray
    seg_slope = (p2_y - p1_y)/(p2_x - p1_x)
    normal_slope = 0 - (1.0 / seg_slope)

    # For y=mx+b form, we need to solve for b (y intercept)
    seg_b = p1_y - seg_slope * p1_x
    normal_b = py - normal_slope * px

    log.debug("Segment line is y= {} * x + {}".format(seg_slope, seg_b))
    log.debug("Normal line is  y= {}  *x + {}".format(normal_slope, normal_b))

    # Combining and subtracting the two line equations to solve for
    x_intersect = (seg_b - normal_b) / (normal_slope - seg_slope)
    y_intersect = seg_slope * x_intersect + seg_b
    # Colinear points are ok! 

    return (x_intersect, y_intersect)

def normal_dist_sqr(seg_p1, seg_p2, p):
    """Square of distance from p to line through seg_p1 to seg_p2
    (even if the segment does not extend to the intersection
    with the normal).  
    Sqrt is expensive, and may not always be needed. 
    """
    ix, iy = normal_intersect(seg_p1, seg_p2, p)
    px, py = p
    dx = px - ix
    dy = py - iy
    dist = dx*dx + dy*dy
    return dist

def normal_dist(seg_p1, seg_p2, p):
    """Distance (not squared) from p to line through segment."""
    return math.sqrt(normal_dist_sqr(seg_p1, seg_p2, p))

def cli_args():
    """
    When invoked from the command line, we create 
    a UTM file (to standard output) 
    from a json file of the form 
    [ [lat, lon], [lat, lon], ... ]
    """
    parser = argparse.ArgumentParser("Measure distance along a json-encoded path")
    parser.add_argument('json_file_in',
                            help="A file containing a json-encoded path",
                            type=argparse.FileType('r'))
    parser.add_argument('utm_file_out',
                            help="Output file is json of utm with distance",
                            type=argparse.FileType('w'))
    args = parser.parse_args();
    return args

if __name__ == "__main__":
    args = cli_args()
    infile = args.json_file_in
    outfile = args.utm_file_out
    points = json.load(infile)
    utm_path, zone = track_to_utm(points)
    json.dump({ "zone": zone, "path": utm_path }, outfile)


