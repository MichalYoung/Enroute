"""
The enroute functionality tied to spot trackers, 
including caching in a MongoDB database. 
"""

import sys
import os
import json
import arrow
import time
import urllib.request
import configparser
from pymongo import MongoClient

import logging
logging.basicConfig(format='%(levelname)s:%(message)s',
                        level=logging.DEBUG)
log = logging.getLogger(__name__)

# Configurable ... 
config = configparser.ConfigParser()
config.read("config.ini")
MONGO_URL=config["DEFAULT"]["mongo_url"]
QUERY_INTERVAL_MINUTES = int(config["DEFAULT"]["query_interval_minutes"])

URL_API = "https://api.findmespot.com/spot-main-web/consumer/rest-api/2.0/public/feed/{}/message.json"

# A time before time, and before spot trackers
EPOCH = arrow.get(0)

client = MongoClient(MONGO_URL)
db = client.enroute
collection = db.tracks

def is_stale(a):
    """a is an arrow object.  It is stale if it is more than 
    QUERY_INTERVAL_MINUTES in the past. 
    """
    now = arrow.now()
    return now > a.replace(minutes=QUERY_INTERVAL_MINUTES)

def get_feeds(feedlist):
    """Retrieve spot information, from cache or directly
    from Spot depending on whether they are stale.
    Output will look like 
      [  { id:  spot_id,  
           latest: { spot observation data }, 
           path: [ points in last hour ] }, 
          ... ]
    """
    feeds = [ ]  
    log.debug("-> get_feeds({})".format(feedlist))
    for feed in feedlist:
        request = { "id": feed }
        record = collection.find_one(request)
        if (record == None):
            log.debug("No record for {}".format(feed))
            record = { "id": feed,
                        "last_query_time":
                           EPOCH.isoformat(), 
                        "latest": { }, 
                        "path": [ ]
                      }
            collection.insert(record)
        last_queried = arrow.get(record["last_query_time"])
        # Note that a bogus "missing" record is always stale,
        # but here we'll update its last query time even if there
        # are no records available from Spot. 
        if is_stale(last_queried): 
                record = spot_direct_query(feed)
                collection.update_one(  {"id": feed },
                                        {"$set": record }  )

        if "_id" in record: 
            del record["_id"]  # Because it isn't JSON serializable
        if "latest" in record and record["latest"] != {}:
            feeds.append(record)
    return feeds

def spot_direct_query(feed):
    """Returns record with fields id, last_query_time, last_observation, path """
    time.sleep(2)
    messages = spot_feed(feed)
    log.debug("Spot observation: {}".format(messages))
    if len(messages) == 0:
        return { "id": feed, "last_query_time": arrow.now().isoformat(),
                 "last_observation": EPOCH.isoformat(), "path": [ ] }
    # So we have at least one observation.
    log.debug("At least one message, handling last")
    last = messages[0]
    last_obs = { "dateTime": last["dateTime"],
                 "latlon":   [ last["latitude"], last["longitude"] ],
                 "batteryState":  last["batteryState"] }

    path = [ ]
    points_expire = arrow.now().replace(hours=-1)
    #points_expire = arrow.now().replace(days=-7)
    for point in messages: 
        if arrow.get(point["dateTime"]) < points_expire:
            break
        path.append([ point["latitude"], point["longitude"] ])
    return { "id": feed, "last_query_time": arrow.now().isoformat(),
                 "latest": last_obs, "path": path }


def spot_feed(feed_id,empty_exception=False):
    """
    Retrieve the last 50 messages from feed.
    Args:
        feed_id:  A spot feed identifier
    Returns:
        list of 'message' objects.  Each message is a dict,
        with attributes including "latitude" and "longitude" and "dateTime"

        Note list may be empty if there are no points to retrieve,
        unless empty_exception is set to True, in which case an
        exception is raised with the Spot error message. 
    """
    URL= URL_API.format(feed_id)
    response = urllib.request.urlopen(URL)
    txt = response.read().decode("utf-8")
    data=json.loads(txt)
    if "errors" in data["response"]:
        if empty_exception:
            msg = data["response"]["errors"]["error"]["description"]
            raise Exception(msg)
        else:
            return [ ]

    points = data["response"]["feedMessageResponse"]["messages"]["message"]
    if isinstance(points,list):
        return points
    else:
        # Spot tracker seems to special-case the singleton
        return [ points ]
    
