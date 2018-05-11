"""Attempt to get event data from
events/event_name.csv
"""

import csv

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

class SpotTrack(object):
    """Record of a rider with a Spot tracker"""

    def __init__(self, rider: str, spot: str, route: str, color: str):
        self.rider = rider
        self.spot = spot
        self.route = route
        self.color = color

    def __repr__(self):
        return f"SpotTrack({self.rider}, {self.spot}, {self.route}, {self.color})"

    def __str__(self):
        return f"(Track {self.rider} on route {self.route}, Spot {self.route}, Color {self.color})"

class Route(object):
    """Information about a track"""

    def __init__(self, abbrev: str, name: str):
        """abbrev is the abbreviated name, e.g., 'eden'
        name is the full name, e.g., 'Eden's Gate 2018'
        """
        self.abbrev = abbrev
        self.name = name

    def __repr__(self):
        return f"Route('{self.abbrev}', '{self.name}')"


class EventRecord(object):
    """Information for an event, from a CSV file."""

    def __init__(self, event_name: str):
        """Loads event info, or sets found flag to false"""
        self.name = event_name
        self.loaded = False
        self.errmsg = "No error message was generated"
        self.title = "Brevet Progress"
        self.riders = [ ]
        self.routes = [ ]
        self.attempt_load()
        log.debug(f"Constructed EventRecord with loaded={self.loaded}")

    def attempt_load(self):
        path = "events/{}.csv".format(self.name)
        try:
            with open(path, newline="") as csvfile:
                log.debug(f"Successfully opened '{path}' as CSV file")
                reader = csv.reader(csvfile)
                for row in reader:
                    log.debug(f"Processing row {row}")
                    if len(row) == 0:
                        continue
                    if row[0].strip().startswith("#"):
                        continue
                    # Content row.  Currently understood commands are
                    # 'event  event-title'
                    # 'route routename'
                    # 'spot routename riderName GID'
                    if row[0] == "event":
                        log.debug(f"event {row}")
                        self.title = row[1]
                        continue
                    if row[0] == "route":
                        log.debug(f"'route' record, row={row}")
                        command, abbrev, name = row[0:3]
                        route = Route(abbrev, name)
                        self.routes.append(route)
                        log.debug(f"Appended route {route}")
                        continue
                    if row[0] == "spot":
                        command, route, name, gid, color = row
                        if  not self.route_is_defined(route):
                            log.debug("Undefined route in rider record")
                            self.errmsg = f"spot command references route {route} which has not been defined"
                            return
                        self.riders.append(SpotTrack(name,gid,route,color))
                        continue
                    self.errmsg = f"Unrecognized command: {row}"
                    return
                if len(self.routes) > 0:
                    log.debug("Setting 'loaded' flag to True")
                    self.loaded = True
        except FileNotFoundError:
            self.errmsg = f"Unable to find information for event '{self.name}'"
            log.debug(f"File '{path}' not found")

    def route_is_defined(self, abbrev):
        for route in self.routes:
            if route.abbrev == abbrev:
                return True
        return False






