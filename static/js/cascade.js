/* 

Enroute.js

     Tracking randonneurs with Spot satellite trackers. 
     
     Michal Young, 2014-2017.
     This version September 2017. 

Example usage (expand lists with more items): 

var options = {
    center:  [44.709248,-122.8550084],
    zoom: 8,
    spot_feeds: [
       { name: "Michal Young",
        feed: "0GiLP5jn9iVj8z8qm90QaTnkpygdAmouk", 
        color: "#0066ff", 
	distances: "DariDartUTM.json"
       }], 
    routes:  [{ points: "DariDart.json",
               distances: "DariDartUTM.json",
               color:  "#196666",
               name: "Dari Dart" }   ],
    utm_file: "DariDartUTM.json"
}; 
var tracking = new Enroute(options);

Adding September 2017:  Route points may be added programmatically 
outside the "options" structure.  This is to allow for literal points
file to be injected into the HTML, reducing the number of round trips
to the server. 

We keep two copies of the 'spot_feeds' data.  One is a simple 
array of the SPOT ids, which we loop through for queries. The 
other is a dictionary with SPOT id as key.  The records in the 
dictionary are augmented with observation and trace data, e.g., 

feeds = [ "0GiLP5jn9iVj8z8qm90QaTnkpygdAmouk", ... ]

riders = {
   "0GiLP5jn9iVj8z8qm90QaTnkpygdAmouk": 
       { name: "Michal Young",
        feed: "0GiLP5jn9iVj8z8qm90QaTnkpygdAmouk", 
        color: "#0066ff", 
        marker: <Leaflet marker object>, // added in show_position, 
	trace: <Leaflet polyline object>, // added in show_path, 
	distances: "DariDartUTM.json"     // may be taken from overall options
       }, 
   ...
}

*/

console.log("Loading dependencies: leaflet, moment"); 

leaflet = require('leaflet');
moment = require('moment');
maki = require('./Leaflet.MakiMarkers.js');

console.log("Constructor of June 2018");

function Enroute(options) {

    console.log("This is version of June 2018")

    var riders = { };    /* Personal *and* rental spots, maps to rider record */
    var feeds = [ ];     /* Personal spots only, a list of gid */
    var tl_feeds = [ ];  /* Rental (TrackLeaders) spots  only, a list of esn */

    /* 
     * Fields in this object: 
     *   this.center :  [ lat, lon ]
     *   this.zoom :  int
     *   this.utm_file: path to file with UTM coordinates and distances
     *   this.riders : { "Spot feed id": { name: "Rider Name",  color: "#0000FF"
     *                                    marker: {Leaflet marker obj }, 
     *                                    trace: Leaflet polyline, 
     *                                    started: iso time string (optional), 
     *                                    route_utm_file: file path (optonal)
     *                                    }, 
     *                  "Spot feed id": { ... } }
     *   this.feeds :  [ "Spot feed id", "Spot feed id", ... ]
     *   this.map : Leaflet map object
     */

    var app_root = "/";
    if ('app_root' in options) {
	    app_root = options.app_root;
    }
    
    if ('center' in options) {
		this.center = options.center;
    } else {
		this.center = [40.8890347,-97.154832]; // U.S.
    }

    if ('zoom' in options) {
		this.zoom = options.zoom;
    } else {
		this.zoom = 5;
    }

    if ('spot_feeds' in options) {
	for (var i=0; i < options.spot_feeds.length; ++i) {
	    var rider = options.spot_feeds[i];
	    var feed = rider.feed;
	    riders[feed] = rider;
	    feeds.push(feed);
	}
    } else {
	    console.log("No spot feeds requested");
    }

    if ('rental_spots' in options) {
	for (var i=0; i < options.rental_spots.length; ++i) {
	    var rider = options.rental_spots[i];
	    var feed = rider.feed;
	    riders[feed] = rider;
	    tl_feeds.push(feed);
	}
    } else {
	    console.log("No trackleader feeds requested");
    }
    console.log("Riders: " + riders);
    console.log("Feeds: " + feeds);
    console.log("Trackleader feeds: " + tl_feeds)


    var utm_file = null;
    if ('utm_file' in options) {
	    utm_file = options.utm_file;
	    this.utm_file = utm_file;
    }

    var checkin_list = [ ] ;  // Iterate over this to track phone check-ins
    var checkins = { } ; // Checkin data goes here, indexed by key
    // Example:
    //    checkin_list = [ { name: "Michal Young", id: "myoung" }, ... ]
    //    checkins = { myoung: { name: "Michal Young", lat: 99.9, lon: 99.9,
    //                           observed: "2017-08-27 13:34:52+0:00" }
    //                 lynnefitz: { ... }
    //                 }
    // 

    if (options.hasOwnProperty("checkins")) {
	    checkins_list = options.checkins;
	    console.log("Got list of phone checkin keys");
    } else {
	    console.log("No phone checkins registered.")
    }

    var map = L.map('map', {center:  this.center, zoom: this.zoom});
    this.map = map;
    console.log("this.map defined")

    L.tileLayer('https://{s}.tiles.mapbox.com/v3/{id}/{z}/{x}/{y}.png',
    {
        attribution: 'Map data <a href="https://mapbox.com">Mapbox</a>',
        maxZoom: 18,
        id: "michalyoung.kc01ifbj"        /* Get this from configuration */
    }).addTo(this.map);

    this.landmark = function(lat, lon, options) {
        var icon = L.MakiMarkers.icon(
	    {  icon: options.icon || "marker-stroked",
	       color: options.color || "#FFFF00",
	       size: "s"
	    });
        var marker = L.marker([lat, lon],
			      { title: options.title || "landmark",
				    icon:  icon,
				    zIndexOffset: -10
			      }).addTo(map);
	
        marker.bindPopup( options.popup || "No description provided" );
    }; 

    
	
    function route_point_describe(latlng, options) {
	    console.log("Describing route point "
		    + latlng + " on " + options.name);
	    if (options.hasOwnProperty("distances")) {
	        console.log("has distances");
	        $.getJSON(app_root + "_along",
		      { lat: latlng.lat,
			    lng: latlng.lng,
			    track: options.distances
			  },
		      function (d) {
			    var dist_km = Math.round(d.result);
			    var dist_mi = Math.round(d.result * 0.6213);
			    var desc = options.name + "\n" +
			      dist_km + "km (" +
			      dist_mi + "mi)";
			    L.popup()
			      .setLatLng(latlng)
			      .setContent(desc)
			      .openOn(map);
		        });
	    } else {
	        console.log("no distances");
	        L.popup()
		    .setLatLng(latlng)
		    .setcontent(options.name)
		    .openOn(map);
	    }
    }
	    

    function plot_route( options ) {
	    var points_file = options.points;
	    $.get(app_root + "_get_route?route=" + points_file,
              function(points) {
		        var route = L.polyline(points,
		            { color: options.color, weight: 6, opacity: 0.5} );
		              route.on('click',
		              function(e) {
		                console.log('click');
		                route_point_describe(e.latlng, options);
		              });
		        route.addTo(map);
		        if (options.zoomto) {
		            console.log("Zooming map to route");
		            map.fitBounds(route.getBounds());
		        } else {
		            console.log("Not centering map");
		        }
	          });
	    console.log("Created route " + options.name);
    }
	
    this.plot_route = plot_route; 

    if ('routes' in options) {
		console.log("Plotting routes ...");
		for (var i=0; i < options.routes.length; ++i) {
	    	    this.plot_route(options.routes[i]);
		}
    }

    /* We will always call the same URL to ask for updates 
     * on all the riders, so we'll calculate the 
     * spot request URL just once. 
     *
     * OBSOLETED June 2018 in favor for chunking
    var spot_query_url= app_root + "_riders";
    var parm_marker = "?feed=";
    for (var i=0; i < feeds.length; ++i) {
	   spot_query_url = spot_query_url + parm_marker + feeds[i];
	   parm_marker = "&feed=";
    }
    console.log("Spot request URL will be " + spot_query_url + "(length " + spot_query_url.length + ")");
    */

    /* CHANGE:  With 25 spots, querying all in a batch with 2 second
     * waits between (to stay within rate limits) can be so slow that we may time out.
     * So, let's break this into smaller requests, up to 5 trackers at a time.
     */

    function chunk_spot_urls() { // Returns list of URL parameter strings for query_spot
        var spot_chunks = [ ]; // A list of URL parameter strings
        var spot_query_url= app_root + "_riders";
        var parm_marker = "?feed=";
        var cur_chunk = spot_query_url;
        var chunk_spot_count = 0
        for (var i=0; i < feeds.length; ++i) {
            cur_chunk = cur_chunk + parm_marker + feeds[i];
            parm_marker = "&feed="
            chunk_spot_count += 1;
            if (chunk_spot_count >= 5) {
                spot_chunks.push(cur_chunk);
                cur_chunk = spot_query_url;
                chunk_spot_count = 0;
                parm_marker = "?feed=";
            }
        }
        if (chunk_spot_count > 0) {
            spot_chunks.push(cur_chunk);
        }
        return spot_chunks;
    }

    var spot_urls_chunks = chunk_spot_urls();
    console.log("Broke personal spots into " + spot_urls_chunks.length + " chunks")
    /* 
     * Expected format of spot observations is 
     * [ { id: spot_id,  latest: { spot observation data }, 
     *     path: [ points in last hour ] }, 
     *   { id:  spot_id,  latest: { spot observation data }, 
     *     path: [ points in last hour ] }, 
     *    ... ]
     */

    /* This function will be called at regular intervals; 
     * See end of this file. 
     */ 
    function query_spots() {
	    for (i=0; i < spot_urls_chunks.length; ++i) {
	    var query_url = spot_urls_chunks[i];
	    console.log("Spot chunk " + i + " of " + spot_urls_chunks.length + ": "+ query_url);
	    $.getJSON(query_url,
	      function(observations) {
		    console.log("Received spot data: " + observations + " length "
			      + observations.length);
		    for (var i=0; i < observations.length; ++i) {
		        console.log("Observation #" + i + " of " +
				  observations.length); 
		        var obs = observations[i];
		        console.log("Received observation of tracker " + obs.id);
		        show_track(obs);
		    }
	      });
	     }
    }

    /* Similarly for trackleaders */
    var tl_query_url= app_root + "_tl_riders";
    parm_marker = "?feed=";
    for (var i=0; i < tl_feeds.length; ++i) {
	   tl_query_url = tl_query_url + parm_marker + tl_feeds[i];
	   parm_marker = "&feed=";
    }
    console.log("Trackleaders request URL will be " + tl_query_url + "(length " + tl_query_url.length + ")");


    /* We also poll trackleaders, at a different URL but otherwise treated
     * similarly.
     */
     function query_tl_spots() {
	    console.log("Sending spot query: " + tl_query_url);
	    $.getJSON(tl_query_url,
	      function(observations) {
		    console.log("Received tl spot data: " + observations + " length "
			      + observations.length);
		    for (var i=0; i < observations.length; ++i) {
		        console.log("Observation #" + i + " of " +
				  observations.length);
		        var obs = observations[i];
		        console.log("Received observation of tl tracker " + obs.id);
		        show_track(obs);  /* Code in common with other spot tracks from here */
		    }
	      });
    }




    function show_track(obs) {
	/* Expecting obs to be 
         * { id:  spot_id,  latest: { spot observation data },
         *   path: [ points in last hour ] }
         */
	    console.log("Show track: latest=" + JSON.stringify(obs.latest));
	    show_position(obs.id, obs.latest);
	    /* show_path(obs.id, obs.path); */
    }

    /* Create a marker if the rider doesn't already have one; 
     * after ensure_marker it is safe to reference rider.marker.
     */
    function ensure_marker( rider, position ) {
	    if (rider.hasOwnProperty("marker")) {
	        return;
	    }
	    console.log("Creating a new marker for " + rider.name +
		    " at " + position); 
        var color = rider.color;
	    var name = rider.name;
        var bicon = L.MakiMarkers.icon({icon: "bicycle",
					color: color, size: "m"});
        var marker = L.marker(position,
			      {  title: name,
				     icon: bicon,
				     riseOnHover: true,
			      }).addTo(map);
	    rider.marker = marker;
	    return marker;
    }

    /* Given an ISO time string, return a humanized description */ 
    function time_desc(time) {
	    console.log("Humanizing time string " + time);
	    obs_time = moment(time);
        var ago = obs_time.fromNow(); 
        var obs_time_str = obs_time.format("hh:mm a<br />ddd MMM D")
            + "<br />(" + ago + ")";
	    return obs_time_str;
    }

    /* Given kilometers measure in full precision, 
     * return formatted description of rounded km and miles; 
     * kilometers == -1 is special case signaling "off course"
     */
    function dist_desc(dist_km) {
	    if (dist_km < 0) {
	        return "off course"
	    }
	    var km_rounded = Math.round(dist_km);
	    var mi_rounded = Math.round(dist_km * 0.6213);
	    var desc = `${km_rounded}km (${mi_rounded}mi)`;
	    return desc;
    }

    /* Describe progress including distance along path */ 
    function describe_progress_d(rider, observation, distances) {
	    console.log("describe_progress_d for rider " + rider.name);
	    ensure_marker(rider);
	    var marker = rider.marker;
	    var time = observation.dateTime;
        var pos = observation.latlon; 
	    /* pos is NOT a latlng object; it's a list of two elements */
	    var lat = pos[0];
	    var lng = pos[1];
	    if (observation.hasOwnProperty("prior_position")) {
	         prior_lat = observation.prior_position[0]
	         prior_lng = observation.prior_position[1]
	    } else {
	         // Default values indicate we don't have a prior observation
	        prior_lat = 0;
	        prior_lng = 0;
	}
	console.log("Querying for lat and lng " +
		    lat + ", " + lng)
	    console.log("  ... using distances file  " + distances);
	    $.getJSON(app_root + "_along",
		  { lat: lat,
		    lng: lng,
		    prior_lat: prior_lat,
		    prior_lng: prior_lng, 
		    track: distances
		  },
		  function (d) {
		      var dist_km = d.result;
		      var desc = "<p>" + rider.name + "<br />" + 
			  time_desc(time) + "<br />" +
			  dist_desc(dist_km) + "</p>";
		      console.log("Binding description " + desc); 
		      marker.bindPopup(desc);
		  });
    }
	
    /* Describe progress as time alone, without distance */
    function describe_progress_t(rider,  latlng, time) {
	    console.log("describe_progress_t for" + rider.name);
	    ensure_marker(rider);
	    var marker = rider.marker;
	    var when_desc = time_desc(time);
	    console.log("Time description: " + when_desc);
	    var desc = "<p>" + rider.name + "<br />" +  when_desc + "</p>" ;
	    console.log("Popup description: " + desc);
	    marker.bindPopup(desc);
    }
	    
    function show_position( id, observation ) {
	    console.log("Handling observation: " + JSON.stringify(observation));
        var position = observation.latlon; 
	    var rider = riders[id];
	    var time = observation.dateTime;
	    ensure_marker(rider, position);
	    var marker = rider.marker;
	    marker.setLatLng(position);
	    if (rider.hasOwnProperty("distances")) {
	      describe_progress_d( rider, observation, rider.distances );
	    } else {
	      describe_progress_t( rider, position, time );
	    }
    }


    function show_path(id, path) {
	    console.log("Plotting trace " + path);
	    var rider = riders[id];
        var name = rider.name;
	    if (rider.hasOwnProperty("trace")) {
            console.log("Updating trace");
            var trace = rider.trace;
            trace.setLatLngs(path);
        } else {
            // First trace for this id
            var trace = L.polyline(
		        path,
                { weight: 4, color: "#ff0000", opacity: 0.9,
                  dashArray: "3,7"
                }).addTo(map);
            rider.trace = trace;
        }
    }

    var minutes = 1000 * 60;
    query_spots(); 
    setInterval( query_spots, 2 * minutes );
    query_tl_spots();
    setInterval( query_tl_spots, 1 * minutes )

}

window.Enroute = Enroute;
