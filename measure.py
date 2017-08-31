"""
Measure distances along a path represented as lat-lon pairs. 
(Experimental August 2017)c
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

# --------------------------------------
# Parameter constants
# --------------------------------------

# Upper bound on distance from mapped route for us
# to calculate a "distance along route"
#
MAX_DEVIANCE_METERS = 3000        # 3km

# --------------------------------------


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

def utm_seg_lengths( path ):
    """For testing: Print the length of each segment, and sum them"""
    sum = 0
    prev = path[0]
    for pt in path:
        e1, n1, d1 = prev
        e2, n2, d2 = pt
        de = e2-e1
        dn = n2-n1
        seg_dist = math.sqrt(de*de + dn*dn)
        sum += seg_dist
        print("Seg {:2F} tot {:2F} should be {:2F}"
                  .format(seg_dist / 1000.0, sum / 1000.0, d2))
        prev = pt

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
        print("{:2,.2f}-{:2,.2f} {:2,.2f} {:2,.2f}  DIFF: {:2,.2f}"
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
        log.debug("dist {:2,.2f} - {:2,.2f} => {:2,.2f}".format(prev, pt, seg_dist_km))
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

def interpolate_route_distance(lat, lon, utm_track, utm_zone):
    """
    If (lat, lon) is within MAX_DEVIANCE_METERS of 
    a segment on utm_track, calculate distance 
    to nearest point. 
    """
    if len(utm_track) == 0:
        return 0
    skipped_point_count = 0
    measured_point_count = 0
    new_min_count = 0
    buffer = MAX_DEVIANCE_METERS
    max_dev_sqr = MAX_DEVIANCE_METERS * MAX_DEVIANCE_METERS
    obs_east, obs_north, _, _ = \
         utm.from_latlon(lat, lon, force_zone_number=utm_zone)
    min_deviance = 2 * max_dev_sqr
    interpolated_dist = 0
    prior = utm_track[0]
    for pt in utm_track[1:]:
        prev = prior
        prior = pt
        east_1, north_1, dist_km_1 = prev
        east_2, north_2, dist_km_2 = pt
        # log.debug("Segment ending at distance {:2,.2f}km".format(dist_km_2))
        if (obs_east + buffer < min(east_1, east_2)
            or obs_east - buffer > max(east_1, east_2)
            or obs_north + buffer < min(north_1, north_2)
            or obs_north - buffer > max(north_1, north_2)):
            skipped_point_count += 1
            continue

        measured_point_count += 1
        log.debug("Observation {:2,.2f},{:2,.2f}".format(obs_east, obs_north))
        log.debug(" measure to {:2,.2f},{:2,.2f}".format(east_1, north_1))
        log.debug("         -> {:2,.2f},{:2,.2f}".format(east_2, north_2))

        close_east, close_north = \
          closest_point(east_1, north_1,
                        east_2, north_2,
                        obs_east, obs_north)
        dev_sqr = dist_sqr(obs_east, obs_north, close_east, close_north)
        log.debug("Measured distance {:2,.2f}km"
                      .format( math.sqrt(dev_sqr) / 1000.0 ))
        if dev_sqr < min_deviance:
            log.debug("New min distance found; interpolating")
            new_min_count += 1
            min_deviance = dev_sqr
            _, _, from_dist = prev
            _, _, to_dist = pt
            frac = (close_east - east_1) / (east_2 - east_1)
            log.debug("Interpolating distance at {:2,f} between ".format(frac))
            log.debug("   between {:2,f}km and {:2,f}km"
                          .format(from_dist, to_dist))
            inter_dist = from_dist + frac * (to_dist - from_dist)
            log.debug("New min distance recorded")
    log.debug("Skipped {}, measured {}, took new min {} times"
                  .format(skipped_point_count,
                              measured_point_count,
                              new_min_count))
    if min_deviance > max_dev_sqr:
        log.debug("Nothing within buffer distance; closest was {}km"
                      .format(math.sqrt(min_deviance)))
        return 0
    return inter_dist

def into_range(val, lim_1, lim_2):
    """Place val into range lim_1 ... lim_2"""
    log.debug("Forcing {:2,f} into range".format(val))
    log.debug("        {:2,f} to".format(lim_1))
    log.debug("        {:2,f}".format(lim_2))
    lim_lower =  min(lim_1, lim_2)
    lim_higher = max(lim_1, lim_2)
    val = max(val, lim_lower)
    val = min(val, lim_higher)
    log.debug("     => {:2,f}".format(val))
    return val

def closest_point(p1_x, p1_y, p2_x, p2_y, px, py):
    """Closest point to (px,py) on s=(p1x,p1y)-(p2x,p2y). 
    It is the point on a normal from p to the line
    that runs through s, but if that normal is beyond
    the extent of s, then it will be at an endpoint
    of the segment. """
    i_x, i_y = normal_intersect(p1_x, p1_y, p2_x, p2_y, px, py)
    log.debug("Intersect ray   at {:2,f}, {:2,f}".format(i_x, i_y))
    log.debug("       on ray      {:2,f}, {:2,f}".format(p1_x, p1_y))
    log.debug("               ->  {:2,f}, {:2,f}".format(p2_x, p2_y))
    i_x = into_range(i_x, p1_x, p2_x)
    i_y = into_range(i_y, p1_y, p2_y)
    log.debug("Adjusted intersect {:2,f}, {:2,f}".format(i_x, i_y))
    return (i_x, i_y)
                                                    

def normal_intersect(p1_x, p1_y, p2_x, p2_y, px, py):
    """
    Find the point at which a line through seg_p1, 
    seg_p2 intersects a normal dropped from p. 
    """

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

    #log.debug("Segment line is y= {} * x + {}".format(seg_slope, seg_b))
    #log.debug("Normal line is  y= {}  *x + {}".format(normal_slope, normal_b))

    # Combining and subtracting the two line equations to solve for
    x_intersect = (seg_b - normal_b) / (normal_slope - seg_slope)
    y_intersect = seg_slope * x_intersect + seg_b
    # Colinear points are ok! 

    return (x_intersect, y_intersect)

def dist_sqr(x1, y1, x2, y2):
    """
    Square of distance between (x1,y1) and (x2,y2)
    (to avoid sqrt except when needed)
    """
    dx = x2 - x1
    dy = y2 - y1
    dsq = dx*dx + dy*dy
    return dsq

# def closest_dist(p1_east, p1_north, 
#                 p2_east, p2_north,
#                 px, py):
#     """Distance (not squared) from p to line through segment."""
#     return math.sqrt(closest_dist_sqr(p1_east, p1_north,
#                                      p2_east, p2_north,
#                                      px, py))

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


