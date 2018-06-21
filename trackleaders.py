"""
Read trackleaders.com full feed, which is XML.  Produce JSON that looks 
pretty much like we get from spot.py. 

This is an aggregated feed, so we don't need delays ... we just read a 
whole feed, which looks like the sample at the end of this file. 



"""


import requests
import xml.etree.ElementTree as ET
import arrow

from typing import List, Dict

# Configured variables
import config
from pymongo import MongoClient
from pymongo import ReplaceOne
MONGO_URL = config.get("mongo_url")
URL = config.get("trackleaders_url")



import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

# Performed once at instantiation
# Database collection
client = MongoClient(MONGO_URL)
db = client.enroute
collection = db.tl_tracks   # TrackLeaders tracks

# Cached access --- we read from MongoDB database,
# optionally refilling the database if the last access
# was more than 1 minute ago.
#


def get_tracks(feed_list: List[str]) -> List[dict]:
    """feed_list is a list of esns.  We return
    a list of dicts representing tracks.  The list includes
    only the requested tracks, which are accessed from the
    database cache.  Cache reload may be triggered if
    last query is older than the polling interval.
    """
    cache_reload_if_stale()
    return tracks_from_cache(feed_list)

def tracks_from_cache(feed_list: List[str]) -> List[dict]:
    """Get just the requested tracks from cache.
    (Thus tracks that TrackLeaders is still reporting, but which
    have been marked inactive in configuration, will not be reported
    back to the map.)
    """
    log.debug(f"Tracks from cache Looking for {feed_list}")
    feeds_requested = set(feed_list)
    feeds = [ ]
    for feed in collection.find():
        if  "id" in feed and feed["id"] in feeds_requested:
            #for feed in feed_list:
            #track = collection.find_one({"id": feed})
            #if track is not None:
                feeds.append(feed)
    log.debug("Done with tracks from cache")
    return feeds



def cache_reload_if_stale():
    """Reload track records into Mongo collection
    if the cache in database is older than
    the polling interval (currently 1 minute).
    Since TrackLeaders is an aggregated feed,
    we don't look at the last query date in each
    record even though we have it.  Instead we
    keep a separate record of last query time and
    re-read the whole aggregate feed if needed.
    """
    # While I might get away with a global variable for the
    # last read time, keeping it in database is safer in case
    # there are multiple instances of this program.
    log.debug("Testing staleness")
    now = arrow.now()
    stale = now.replace(minutes=-1)
    request = { "trackleaders_poll": "poll_record" }
    record = collection.find_one(request)
    if record is None:
        log.debug("No prior poll record")
        collection.insert( {"trackleaders_poll": "poll_record",
              "last_query_time": now.isoformat()
             })
        cache_reload()
    elif arrow.get(record["last_query_time"]) < stale:
        log.debug("Trackleaders cache is stale")
        collection.update_one( {"trackleaders_poll": "poll_record"},
             { "$set": {"last_query_time": now.isoformat() }})
        cache_reload()
    else:
        log.debug("Would be using existing cache")
        #FIXME:  nothing to do here?
    log.debug("Done with test/reload")

def cache_reload():
    """Cache is stale; reload it here."""
    log.debug("Reloading cache")
    text = pull()
    messages = extract(text)
    tracks = reformat(messages)
    log.debug("Updating Mongo")
    requests = [ ]
    for track in tracks:
        requests.append(ReplaceOne({"id": track["id"]}, track, upsert=True))
        #record = collection.find_one(request)
        #if record is None:
        #   collection.insert_one(track)
        #else:
        #   collection.update_one(request, {"$set": track})
    result = collection.bulk_write(requests)
    log.debug(f"Done  updating Mongo, replaced {result.modified_count}")
    log.debug("Done reloading cache")


def pull() -> str:
    log.debug("pull")
    try:
        r = requests.get(URL)
        log.debug(f"Status code: {r.status_code}")
        text = r.text
        log.debug("Done with pull")
        return text
    except requests.RequestException as e:
        print(f"Exception {e}")
        raise e

def extract(txt: str) -> List[dict]:
    """
    Returns extracted list of dicts, each dict representing
    a "message" element with its children being key:value pairs
    in the dict.  Keys and values are as they appear in the
    TrackLeaders feed, without any selection or further processing.

    The "design secret" of this function is the XML element
    hierarchy of the TrackLeaders feed.
    """
    log.debug("Extract")
    root = ET.fromstring(txt)
    #log.debug(f"Type of root is {type(root)}, should be trackleaders_aggregate_feed")
    #log.debug(f"Tag of root is {root.tag}, type {type(root.tag)}")
    messages = [ ]
    for feed in root:
        #log.debug(f"   Child of root, tag is {feed.tag}; should be trackleaders_feed")
        for message in feed:
            #log.debug(f"      Tag is {message.tag}, we are looking for 'message'")
            if message.tag != 'message':
                #log.debug(f"Skipping {message.tag}")
                continue
            message_dict = { }
            for element in message:
                key = element.tag
                value = element.text
                #log.debug(f"Saving pair ({key}, {value})")
                message_dict[key] = value
            messages.append(message_dict)
    log.debug("Done  with extract")
    return messages

def reformat(messages: List[dict]) -> List[dict]:
    """Takes list of messages in TrackLeaders format and
    delivers list of tracks in format as similar as possible
    to what we produce for a spot feed.
    Input looks like:
    [{'id': '993354437',
    'esn': '0-2578655',
    'esnName': 'T305c',
    'messageType': 'UNLIMITED-TRACK',
    'messageDetail': None,
    'timestamp': '2018-06-12T18:17:23.000Z',
    'timeInGMTSecond': '1528827443',
    'latitude': '40.11396',
    'longitude': '95.7913',
    'batteryState': 'LOW',
    'elevation': '-1.000000'},
     ...
     ]

    Result should look like

    { "id": "0-2578655",  # This will be from esn, not from the id field
      "last_query_time": '2018-06-19T19:39:37.712494-07:00', # Time of query, not of spot message
      "latest": { "dateTime": '2018-06-19T19:39:37.712494-07:00',
                  "latlon":   [ 40.11396, 95.7913],
                  "batteryState":  "LOW" },
      "path": [[40.11396, 95.7913], [40.11400, 95.7928], ... ]
    }
    latlon pairs in path are those from messages fresher than expiration time.
    latest is from the most recent observation of a tracker.
    """
    log.debug("Reformatting messages")
    now = arrow.now().isoformat()
    #FIXME: real messages will expire in an hour, not a month
    expires = arrow.now().replace(hours=-1)
    # Pass 1: We build up a dict keyed by esn.  Each
    # value in dict will become an element of the output list.
    table = {}
    for msg in messages:
        esn = msg["esn"]
        if esn not in table:
            initial = {
                "id": esn,
                "last_query_time": now,
                "latest": {
                    "dateTime": arrow.get(msg["timestamp"]).isoformat(),
                    "latlon": [float(msg["latitude"]), float(msg["longitude"])],
                    "batteryState": msg["batteryState"]
                },
                "path": [ ]
            }
        table[esn] = initial
        # Now we know it is in the table, so the question is whether to replace
        # the latest observation. Points seem to occur in backwards time order,
        # although this is not documented.  (Nothing is documented.)
        # I'm going to hope I can count on that,
        # so I don't need to sort points.  If I *do* need to sort points, it may be
        # simpler to just sort the collection of messages by time-stamp; that way no
        # need to tag each path component with a time.
        # First: Too old?
        observed_at = arrow.get(msg["timestamp"])
        if observed_at < expires:
            #log.debug(f"Message expired at {observed_at} (earlier than {expires}")
            continue
        # Within observation window.
        track = table[esn]
        if observed_at > arrow.get(track["latest"]["dateTime"]):
            log.warn("Newer observation replacing latest!")
            # FIXME  If I ever see this warning, I need to handle out-of-order messages
        point = [float(msg["latitude"]), float(msg["longitude"])]
        track["path"].append(point)
    # After all messages, we need to convert from dict to list
    log.debug("Done reformatting")
    return list(table.values())


if __name__ == "__main__":
    # cache_reload_if_stale()
    # Test list from sample feed:
    print(get_tracks(["0-2511053", "0-3159988", "0-3130709"]))


"""
Sample (excerpt) of feed, 
  from http://trackleaders.com/spot/ultragobi18/fullfeed.xml

<trackleaders_aggregate_feed>
<trackleaders_feed>
<trackleaders_racer_ID>1</trackleaders_racer_ID>
</trackleaders_feed>
<trackleaders_feed>
<trackleaders_racer_ID>2</trackleaders_racer_ID>
</trackleaders_feed>
<trackleaders_feed>
<trackleaders_racer_ID>3</trackleaders_racer_ID>
<message>
<id>993354437</id>
<esn>0-2578655</esn>
<esnName>T305c</esnName>
<messageType>UNLIMITED-TRACK</messageType>
<messageDetail/>
<timestamp>2018-06-12T18:17:23.000Z</timestamp>
<timeInGMTSecond>1528827443</timeInGMTSecond>
<latitude>40.11396</latitude>
<longitude>95.7913</longitude>
<batteryState>LOW</batteryState>
<elevation>-1.000000</elevation>
</message>
<message>
<id>993350560</id>
<esn>0-2578655</esn>
<esnName>T305c</esnName>
<messageType>UNLIMITED-TRACK</messageType>
<messageDetail/>
<timestamp>2018-06-12T18:12:15.000Z</timestamp>
<timeInGMTSecond>1528827135</timeInGMTSecond>
<latitude>40.11379</latitude>
<longitude>95.79116</longitude>
<batteryState>LOW</batteryState>
<elevation>-1.000000</elevation>
</message>

...

</trackleaders_feed>
</trackleaders_aggregate_feed>
"""
