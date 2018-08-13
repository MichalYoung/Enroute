"""
Serve Spot tracking pages, including 
AJAX updates of tracks. 

"""

import os
import flask
from werkzeug.utils import secure_filename

import json
import logging
import config

import arrow      

import spot
import measure
import event_reader
# import device_assignments
# import trackleaders


###
# Globals
###
app = flask.Flask(__name__)
app.debug=config.get("debug")
app.logger.setLevel(logging.DEBUG)
if app.debug:
    app.logger.setLevel(logging.DEBUG)

# Secret stuff
MAPBOX_TOKEN = config.get("mapbox_token")
app.secret_key = config.get("app_key")

# For configuration from spreadsheets
UPLOAD_FOLDER = "UPLOADS"
ALLOWED_EXTENSIONS = set(['xlsx'])
SUSAN_PW = config.get("susan_pw")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

###
# Pages
###

@app.route("/")
def root():
    app.logger.debug("Entering at root, checking config")
    try:
        root = config.get("root")
        app.logger.debug(f"config returned rooot '{root}'")
        return flask.redirect(root)
    except Exception as e:
        app.logger.debug(f"Exception {e} looking for root in config")
        app.logger.debug("No root configured")
    return flask.redirect(flask.url_for("index"))

@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  app.logger.debug("Note url_for('root') is {}"
                     .format(flask.url_for("root")))
  return flask.render_template("index.html")



### Experimental: Phone checkin
@app.route('/checkin')
def checkin():
    return flask.render_template("checkin.html")

@app.route('/fleche')
def fleche():
    app.logger.debug("Fleche 2018")
    publish_globals()
    return flask.render_template('fleche.html')

@app.route('/alsea')
def alsea():
    app.logger.debug("Alsea")
    publish_globals()
    return flask.render_template('alsea.html')

@app.route('/cascade')
def cascade():
    app.logger.debug("Cascade 1200")
    event_record = event_reader.EventRecord("cascade")
    # spots = device_assignments.get_assignments()
    spots = [ ]
    app.logger.debug(f"event_record.landmarks: {event_record.landmarks}")
    if event_record.loaded:
        flask.g.event = event_record
        flask.g.spots = spots
        publish_globals()
        return flask.render_template('cascade.html')
    else:
        return flask.render_template('404.html'), 404

# Let's try to generalize the event rides ...
@app.route('/event/<name>')
def event(name=None):
    app.logger.debug(f"Looking for {name}'")
    event_record = event_reader.EventRecord(name)
    if event_record.loaded:
        flask.g.event = event_record
        publish_globals()
        return flask.render_template('event.html')
    else:
        return flask.render_template('404.html'), 404

# Experimental support of sidebar
@app.route('/event2/<name>')
def event2(name=None):
    app.logger.debug(f"Looking for {name}'")
    event_record = event_reader.EventRecord(name)
    if event_record.loaded:
        flask.g.event = event_record
        publish_globals()
        return flask.render_template('event2.html')
    else:
        return flask.render_template('404.html'), 404


@app.route('/along')
def along():
    app.logger.debug("Entering along(route)")
    route = flask.request.args.get("route", None)
    gid = flask.request.args.get("gid", None)
    name = flask.request.args.get("name", "A Nonny Mouse")
    app.logger.debug("Tracking route {}, spot {}".format(route,gid))

    flask.g.gid = gid
    flask.g.route = route
    flask.g.name = name
    
    app.logger.debug("/along with gid='{}', route='{}'"
                         .format(flask.g.gid, flask.g.route))
    
    # Error checking: Does this route name match files in
    # the static/routes directory? We expect to see
    # routename_points.json and routename_dists.json.
    points_file_name = os.path.join("static", "routes",
                                        route + "_points.json")
    dists_file_name = os.path.join("static", "routes",
                                       route + "_dists.json")
    if not os.path.isfile(points_file_name):
        app.logger.warn("No such points file '{}'".format(points_file_name))
        flask.g.missing=points_file_name
        return flask.render_template("missing_file.html")
    if not os.path.isfile(dists_file_name):
        app.logger.warn("No such distances file '{}'".format(dists_file_name))
        flask.g.missing=dists_file_name
        return flask.render_template("missing_file.html")
    return flask.render_template('along.html')



@app.route('/def_ride')
def def_ride():
    return flask.render_template('define_ride.html')

@app.route('/susan')
def susan():
    return flask.render_template('susan.html')


######
#  Form handlers (not Ajax)
#####

@app.route('/_trackme')
def initiate_tracker():
    route = flask.request.args.get("route", type=str)
    spot_url =  flask.request.args.get("spot_url", type=str)
    rider_name= flask.request.args.get("rider_name", type=str)
    if spot_url != "": 
        spot_fields = spot_url.split("=")
        gid = spot_fields[-1]
        app.logger.debug("Checking spot feed {}".format(gid))
        spot_ok, msg = spot.spot_gid_valid(gid)
        if not spot_ok:
            flask.flash("Spot checker URL problem: {}".format(msg))
            return flask.redirect(flask.url_for("index"))
    return flask.redirect(flask.url_for("along",route=route,
                                             gid=gid,
                                             name=rider_name))
    # return flask.redirect(flask.url_for("utm_test",route=route,
    #                                         gid=gid,
    #                                   name=rider_name))

@app.route('/_configure_c12', methods=["POST"])
def configure_c12():
    try:
        app.logger.debug(f"flask.request is {flask.request}")
        app.logger.debug(f"flask.request.files is {flask.request.files}")
        for f in flask.request.files:
            app.logger.debug(f"flask.request.files['{f}'] = {flask.request.files[f]}")
        if 'file' not in flask.request.files:
            flask.flash("File not provided")
            flask.flash(f"request.files is '{flask.request.files}'")
            return flask.redirect(flask.url_for("susan"))
        file = flask.request.files['file']
        if file.filename == "":
            flask.flash("File not provided (empty)")
            return flask.redirect(flask.url_for("susan"))
        if flask.request.form["password"] != SUSAN_PW:
            flask.flash("That's not Susan's password. Thick of the chickens.  All lower case, three words.")
            return flask.redirect(flask.url_for("susan"))
        if allowed_file(file.filename):
            filename = secure_filename(file.filename)
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(path)
            flask.flash(f"Uploaded {file.filename}")
            device_assignments.configure(path)
            flask.flash(f"Configured from {path}")
            return flask.redirect(flask.url_for("susan"))
        else:
            flask.flash("Wrong file type; I need the Excel .xlsx file")
            return flask.redirect(flask.url_for("susan"))
    except Exception as e:
        flask.flash(f"D'oh.  Encountered internal error: {e}")
        return flask.redirect(flask.url_for("susan"))


def allowed_file(filename):
    return '.' in filename and \
      filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


######
# Ajax handlers
######

@app.route('/_checkin', methods=["POST"])
def _checkin():
    """AJAX responder to checkin"""
    app.logger.debug("Received _checkin")
    return json.dumps( { "reply": "Got it" } )


@app.route('/_along')
def _along():
    """AJAX responder to request for distance along path"""
    app.logger.debug("Ajax request for distance along path")
    try:
        lat = flask.request.args.get('lat', None, type=float)
        lon = flask.request.args.get('lng', None, type=float)
        prior_lat = flask.request.args.get('prior_lat', None, type=float)
        prior_lng = flask.request.args.get('prior_lng', None, type=float)
        app.logger.debug("lat, lon = {}, {}".format(lat, lon))
        track_file = flask.request.args.get('track', '', type=str)
        file_path = os.path.join("static", "routes",
                                     track_file)
        with open(file_path) as f:
            track_obj = json.load(f)
            assert type(track_obj) == dict, "Distances file must be dict"
            assert "path" in track_obj and "zone" in track_obj, \
                 "Distances file must be object with UTM path and zone"
            if prior_lat or prior_lng:
                dist = measure.interpolate_route_distance(lat, lon,
                                        track_obj["path"], track_obj["zone"],
                                        (prior_lat, prior_lng))
            else: 
                dist = measure.interpolate_route_distance(lat, lon,
                        track_obj["path"], track_obj["zone"])
            app.logger.debug("Interpolated distance {:4,f}".format(dist))
            return flask.jsonify(result=dist)
    except FileNotFoundError as e: 
        app.logger.warn("File {} not found".format(track_file))
        return flask.jsonify(result=0)
    except Exception as e:
        app.logger.warn("_along is broken... {}".format(e))
        raise
        # return flask.jsonify(result=0)
        

@app.route('/_get_route', methods=['GET'])
def get_route():
    """
    Get the coordinates list for a GPX file
    """
    app.logger.debug("Ajax request for route ")
    route = flask.request.args.get("route", type=str)
    app.logger.debug("Attempting send from static/routes/{}"
                         .format(route))
    return flask.send_from_directory('static/routes', route)


@app.route('/_riders', methods=['GET'])
def get_riders():
    """
    Ajax request for rider tracks
    """
    app.logger.debug("Ajax request for riders ")
    riders = flask.request.args.getlist("feed", type=str)
    app.logger.debug("Getting feeds for {}".format(riders))
    tracks = spot.get_feeds(riders)
    # return jsonify(result=result)
    app.logger.debug("Sending tracks: |{}|".format(tracks))
    return json.dumps(tracks)


# @app.route('/_tl_riders', methods=['GET'])
# def get_tl_riders():
#     """
#     Ajax request for rider tracks
#     """
#     app.logger.debug("Ajax request for trackleader riders ")
#     riders = flask.request.args.getlist("feed", type=str)
#     app.logger.debug("Getting trackleader feeds for {}".format(riders))
#     tracks = trackleaders.get_tracks(riders)
#     # return jsonify(result=result)
#     app.logger.debug("Sending tracks: |{}|".format(tracks))
#     return json.dumps(tracks)



####
# Ajax for database lookups
####

# @app.route('/_check_route', methods=['GET'])
# def check_route():
#     """
#     Check database for a route matching a key. Returns a 
#     name if it exists.  Indictates validity with a flag. 
#     """
#     app.logger.debug("Checking for route in database")
#     return 

 
##################
#
# Functions used by routes
#
##################

def publish_globals():
    """Global values that should be available through
    the g object. 
    """
    flask.g.mapbox_token = MAPBOX_TOKEN

def load_points(file_path):
    """Track points as an object that we can plug 
    right into the web page. 
    """
    try: 
        with open(file_path) as f:
            points_obj = json.load(f)
            assert type(points_obj) == list, "Expecting an array of points"
            return points_obj
            
    except FileNotFoundError as e: 
        app.logger.warn("File {} not found".format(file_path))
        raise
    except Exception as e:
        app.logger.warn("load_points is broken... {}".format(e))
        raise

def load_distances(file_path): 
    """UTM paths with distances"""
    try: 
        with open(file_path) as f:
            track_obj = json.load(f)
            assert type(track_obj) == dict, "Distances file must be dict"
            assert "path" in track_obj and "zone" in track_obj, \
                 "Distances file must be object with UTM path and zone"
            return track_obj
    except FileNotFoundError as e: 
        app.logger.warn("File {} not found".format(track_file))
        return flask.jsonify(result=0)
    except Exception as e:
        app.logger.warn("_along is broken... {}".format(e))
        raise
        # return flask.jsonify(result=0)



##################
#
# Error handling
#
##################


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    flask.session['linkback'] =  flask.url_for("index")
    return flask.render_template('404.html'), 404

@app.errorhandler(403)
def page_not_found(error):
    app.logger.debug("403: Forbidden")
    flask.session['linkback'] =  flask.url_for("index")
    return flask.render_template('403.html'), 403

@app.errorhandler(500)
def page_not_found(error):
    app.logger.debug("500: Internal error")
    flask.session['linkback'] =  flask.url_for("index")
    return flask.render_template('500.html'), 500


#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try: 
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

#############
#    
# Set up to run in gunicorn or 
# stand-alone. 
#
app.secret_key = "fixme please"
app.debug=logging.DEBUG
app.logger.setLevel(logging.DEBUG)
if __name__ == "__main__":
    print("Opening for global access on port {}".format(5000))
    app.run(port=5000, host="0.0.0.0")

