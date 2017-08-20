"""
Serve Spot tracking pages, including 
AJAX updates of tracks. 

"""

import os
import flask
from werkzeug.utils import secure_filename

import json
import logging
import configparser

import arrow      
import subprocess

import spot


###
# Globals
###
app = flask.Flask(__name__)
app.logger.setLevel(logging.DEBUG)  # FIXME: from config file

###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  return flask.render_template("eclipse.html")

# FIXME: We should pick out a particular event based
# on URL.  It should be a variable and read from
# config file or database
@app.route('/eclipse')
def eclipse():
    return flask.render_template("eclipse.html")


######
# Ajax handlers
######

@app.route('/_get_route', methods=['GET'])
def get_route():
    """
    Get the coordinates list for a GPX file
    """
    app.logger.debug("Ajax request for route ")
    route = flask.request.args.get("route", type=str)
    route_filename = route + ".json"
    app.logger.debug("Attempting send from static/routes/{}"
                         .format(route_filename))
    return flask.send_from_directory('static/routes', route_filename)

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

 
##################
#
# Functions used by routes
#
##################



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

