Database schema notes.
# Schema notes for Enroute2

Databases are in MongoDB, which is "schemaless", but a schema is defined by the pattern of access and the expected fields.

Three collections:

* Tracks:  Spot satellite tracks. May be expanded to other kinds of tracks in the future. 

* Routes:   Not currently used.  Intended to contain
  { route_name: string,
    points: [ (lat, lon), (lat,lon), ... ]
  }
  
* Rides:  Named (event) rides; used to choose other data from other collections to populate a page. (In development)

* Checkins:  Future expansion for tracking mobile phone tracks with geolocation

##Tracks   

    Example:  {
    "_id": {
        "$oid": "5998ec4d997264b5ac6cca1d"
    },
    "id": "0GiLP5jn9iVj8z8qm90QaTnkpygdAmouk",
    "last_query_time": "2017-12-10T00:51:44.158662+00:00",
    "latest": {
        "dateTime": "2017-12-06T03:05:41+0000",
        "latlon": [
            44.02266,
            -123.1291
        ],
        "batteryState": "GOOD",
        "prior_position": [
            44.02196,
            -123.13736
        ]
    },
    "path": [[lat, lon], [lat, lon], ... ]
}

Path is for points in the last hour, and may be empty if there are no recent observations.
Last query time may be in 1970 (specifically  "1970-01-01T00:00:00+00:00" ) if we have no observations on record.

##Routes

Example:

    {
    "_id": {
        "$oid": "59b6ba9d170dd179ca4e11df"
    },
    "route": 1726,
    "name": "Alsea Loop 200k",
    "desc": "200k loop mostly north and west of Eugene",
    "track": [  [ 44.02619,   -123.09407],	[ lat, lon ], ...   ],
    "distances": {  "zone": 10,
        "path": [
            [  492461.3396804774,  4874786.014262883, 0 ],
            [  491974.94009981334, 4874822.12908919, 0.48793329532628493 ],
            [  easting, norhthing, distance ]
 	 ]
     }
    }
 
Note distances points are in UTM (meters east and north from zone origin) to simplify calculation of distance from the path.  The arrays are parallel:  There is a one-to-one correspondence between [lat,lon] and [east,north,dist].  Distances are in kilometers. 

##Rides
What we want here is all the required information to populate a page for a given event with multiple riders.  Could include multiple routes (e.g., multiple days of a 1200k, multiple teams on a fleche). 

What we need: 

* Name: Key to look up event in database
* Title: For the ride tracking page.  Default to name?
* Routes: [ {route: 1726,  color: "#FF0000" } ] where each route matches the 'route' field of a route in the routes collection.  
   * Issue:  How do we handle non-permanent routes, like fleche team routes? 
* Riders: [ rider, rider, rider, ... ]  where rider is 

	```
	{ name: "Lily McGee", 	
     spot: "0GiLP5jn9iVj8z8qm90QaTnkpygdAmouk", 
     color: "#FF0000", route: 1726 }
     ```
     

     

