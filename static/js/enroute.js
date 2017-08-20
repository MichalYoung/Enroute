/* 

Enroute.js

     Tracking randonneurs with Spot satellite trackers. 
     
     Michal Young, 2014-2015.
     This version August 2017. 

*/

console.log("Loading dependencies: leaflet, moment"); 

leaflet = require('leaflet');
moment = require('moment');
maki = require('./Leaflet.MakiMarkers.js');

console.log("Constructor of August 2017");

function Enroute(options) {

    console.log("This is version of August 2017")

    /* 
     * Fields in this object: 
     *   this.center :  [ lat, lon ]
     *   this.zoom :  int
     *   this.riders : { "Spot feed id": { name: "Rider Name",  color: "#0000FF"
     *                                    marker: {Leaflet marker obj }, 
     *                                    trace: Leaflet polyline }, 
     *                  "Spot feed id": { ... } }
     *   this.feeds :  [ "Spot feed id", "Spot feed id", ... ]
     *   this.map : Leaflet map object
     */
    
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

    var riders = { };
    var feeds = [ ]
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
    console.log("Riders: " + riders);
    console.log("Feeds: " + feeds);


    var map = L.map('map', {center:  this.center, zoom: this.zoom});
    this.map = map;
    console.log("this.map defined")

    L.tileLayer('https://{s}.tiles.mapbox.com/v3/{id}/{z}/{x}/{y}.png',
    {
    attribution: 'Map data <a href="https://mapbox.com">Mapbox</a>', 
    maxZoom: 18,
    id: "michalyoung.kc01ifbj"
    }).addTo(this.map);

    this.landmark = function(lat, lon, options) {
        var icon = L.MakiMarkers.icon(
	    {icon: options.icon || "marker-stroked",
	     color: options.color || "#FFFF00", 
	     size: "s"});
        var marker = L.marker([lat, lon],
			      {
				  title: options.title || "landmark",	
				  icon:  icon, 
				  zIndexOffset: -10
			      }).addTo(map);
	
        marker.bindPopup( options.popup || "No description provided" );
    }; 
    
	
    this.plot_route = function(routename, rgb, title) {
	console.log("Requesting track for " + routename);
	$.get("_get_route?route="+routename,
              function(points) {
		  var route = L.polyline(points,
					 { color: rgb, weight: 6, opacity: 0.5} );
		  if (title != "") {
		      console.log("Attempting to add popup " + title);
		      route.bindPopup(title);
		  }
		  route.on('mouseover', function(e) {
                      console.log("mouseover");
		      this.bringToFront();
  		  });
		  console.log("Attempting to add route to map");
		  route.addTo(map);
		  console.log("Plotted track for " + routename); 
	      })
    }; 

    if ('routes' in options) {
		console.log("Plotting routes ...");
		for (var i=0; i < options.routes.length; ++i) {
	    	var route = options.routes[i]
	    	var gpx = route.gpx;
	    	var color = route.color;
	    	var name = '';
	    	if (route.hasOwnProperty('name')) {
				name = route.name;
				console.log("Route is named " + name); 
	   		}
	    	this.plot_route(gpx, color, name);
		}
    }

    /* Markers and traces are records of the position and trajectory information 
     * we have already created for each spot ID.  Consider them like dicts (hash tables) 
     * indexed by id.  The first time we get data on a rider, we create the marker and trace 
     * for that rider. 
     */
    var markers = { };
    var traces = { };

    /* We will always call the same URL to ask for updates on all the riders, so we'll calculate the 
     * spot request URL just once. 
     */
    var spot_query_url="_riders";
    var parm_marker = "?feed=";
    for (var i=0; i < feeds.length; ++i) {
	spot_query_url = spot_query_url + parm_marker + feeds[i];
	parm_marker = "&feed=";
    }
    console.log("Spot request URL will be " + spot_query_url);


    /* 
     * Expected format of spot observations is 
     * [ { id: spot_id,  latest: { spot observation data }, path: [ points in last hour ] }, 
     *   { id:  spot_id,  latest: { spot observation data }, path: [ points in last hour ] }, 
     *    ... ]
     */

    /* This function will be called at regular intervals; 
     * See end of this file. 
     */ 
    function query_spots() {
	console.log("Sending spot query: " + spot_query_url); 
	$.getJSON(spot_query_url,
	      function(observations) {
		  console.log("Received spot data: " + observations + " length "
			      + observations.length);
		  for (var i=0; i < observations.length; ++i) {
		      console.log("Observation #" + i + " of " + observations.length); 
		      var obs = observations[i];
		      console.log("Received observation of tracker " + obs.id);
		      show_track(obs);
		  }
	      });
    }


    function show_track(obs) {
	/* Expecting obs to be 
         * { id:  spot_id,  latest: { spot observation data }, path: [ points in last hour ] }
         */
	show_position(obs.id, obs.latest);
	show_path(obs.id, obs.path);
    }

    function show_position( id, observation ) {
	console.log("Handling observation: " + observation);
        var position = observation.latlon; 
	var rider = riders[id]; 
        var name = rider.name;
        var obs_time = moment(observation.dateTime);
        var ago = obs_time.fromNow(); 
        var obs_time_str = obs_time.format("hh:mm a<br />ddd MMM D")
            + "<br />(" + ago + ")";
	console.log("Observation is for " + name + " at " + obs_time_str);
        if (rider.hasOwnProperty("marker")) {
            console.log("Updating existing marker");
            var marker = rider.marker;
            marker.setLatLng(position);
            marker.bindPopup("<b>" + name + "</b><br />" + obs_time_str );
        } else {
	    console.log("Creating a new marker for " + name);
            // Initial marker structure
            var color = rider.color;
            var bicon = L.MakiMarkers.icon({icon: "bicycle",
					    color: color, size: "m"});
            var marker = L.marker(position,
				  {
				      title: name,
				      icon: bicon, 
				      riseOnHover: true, 
				  }).addTo(map);
	    
            marker.bindPopup("<b>" + name  + "</b> <br />" + obs_time_str);
            rider.marker = marker;
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

}

window.Enroute = Enroute;
