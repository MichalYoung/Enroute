"""
Tests of distance-along-route calculations including 
directional filtering. 

We will test against Alsea Loop route, which has some 
segments traversed in only one direction and some traversed
in both directions.

Sample points for testing measurement	Lat	Lon
Hwy 36 Cheshire to Territorial:   44.190241,	-123.282513
Territorial and High Pass:	      44.215224,	-123.286637
Alvadore/Dorsey and 36:	          44.193785,	-123.242134
High Pass and 36:	              44.215266,	-123.239881
Territorial south of Monroe: 	  44.258942,	-123.292546
Territorial near Monroe:	      44.309515,	-123.296244

Note:  Distance between Territoral and Alvadore roads 
(northbound and southbound routes) was close enough that I 
had to tighten tolerance from 3km to 2km to avoid Alvadore 
road points being measured along Territorial road, although
they would not have been the closest points if routes went
both ways. 
"""

import measure
import json
import logging

# measure.log.setLevel(logging.DEBUG)

Cheshire_Territorial = (44.190241,	-123.282513)
Territorial_HighPass = (44.215224,	-123.286637)
Alvadore_36 = (44.193785,	-123.242134)
HighPass_Dorsey = (44.215203, -123.240302)
Territorial_South = (44.258942,	-123.292546)
Territorial_Monroe = (44.309515,	-123.296244)
Alvadore_south = (44.143246, 	-123.259785)
dists_path = "static/routes/Alsea_dists.json"

def dist(from_point, to_point, dists, desc=""):
    to_east, to_north = to_point
    measured = measure.interpolate_route_distance(
        to_east, to_north, dists["path"], dists["zone"],
        prior_obs =from_point)
    if desc:
        print("{:1f}km  {}".format(measured, desc))
    return measured

                                    

with open(dists_path) as track:
    track_obj = json.load(track)
    # print(track_obj)
    assert "path" in track_obj and "zone" in track_obj, \
      "Distances file must be object with UTM path and zone"

    # We traverse Territorial north into Monroe and again
    # South from Monroe; we should be farther along on the
    # return segment
    terr_northbound = dist(Cheshire_Territorial,Territorial_South,
                        track_obj, 
                        "Territorial northbound, south of Monroe") 
    terr_southbound = dist(Territorial_Monroe, Territorial_South,
                            track_obj,
                        "Territorial southbound, south of Monroe")
    assert terr_northbound > 0, "Positive distance northbound"
    assert terr_southbound > 0, "Positive distance southbound"
    assert terr_southbound > terr_northbound, "Farther on return"

    # We traverse Dorsey (becomes Alvadore) only southbound,
    # from the intersection with High Pass to the intersection
    # with 36.  We should get positive distance only for
    # southbound travel
    dorsey_southbound = dist(HighPass_Dorsey, Alvadore_36,
                                 track_obj,
                                 "Alvadore and 36, southbound on Dorsey")
    # measure.log.setLevel(logging.DEBUG)
    dorsey_northbound = dist(Alvadore_south, Alvadore_36,
                                 track_obj, 
                                 "High pass and Dorsey, northbound")
    assert dorsey_southbound > 150.0, "Dorsey southbound late in ride"
    assert dorsey_northbound < 0.0, "Never ride Dorsey northbound"

     
