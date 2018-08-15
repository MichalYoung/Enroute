"""Attempt to get event data from
events/event_name.csv
"""

import csv
import argparse

import logging
logging.basicConfig()
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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

    def __init__(self, abbrev: str, name: str, color: str):
        """abbrev is the abbreviated name, e.g., 'eden'
        name is the full name, e.g., 'Eden's Gate 2018'
        """
        self.abbrev = abbrev
        self.name = name
        self.color = color

    def __repr__(self):
        return f"Route('{self.abbrev}', '{self.name}')"

class Landmark(object):
    """Information about a landmark."""
    def __init__(self, kind, lat, lon, icon, title, desc, color):
        # All parameters are str, even though some
        # will become numbers in JavaScript
        self.lat = lat
        self.lon = lon
        self.icon = icon
        self.desc = desc
        self.title = title
        self.color = color

    def __repr__(self):
        return (f"Landmark({self.lat}, {self.lon}, icon={self.icon}, "
               + f"title={self.title}, desc={self.desc}, color={self.color}")

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
        self.landmarks = [ ]
        self.attempt_load()
        log.debug(f"Constructed EventRecord with loaded={self.loaded}")

    def _row_event(self, row: list):
        """Row beginning with 'event' indicates title of event"""
        self.title = row[1]
        return

    def _row_route(self, row: list):
        """Map a route name to route files"""
        log.debug(f"'route' record, row={row}")
        if len(row) == 3:
            row.append("#196666") # Default path color
        command, abbrev, name, color = row[0:4]
        route = Route(abbrev, name, color)
        self.routes.append(route)
        log.debug(f"Appended route {route}")
        return

    def _row_spot(self, row: list):
        log.debug(f"Reading spot record: {row}")
        command, route, name, gid, color = row
        if  not self.route_is_defined(route):
            log.debug("Undefined route in rider record")
            raise InputError(f"Undefined route reference in {row}")
        self.riders.append(SpotTrack(name,gid,route,color))
        return

    def _row_landmark(self, row: list):
        """Landmarks can be control, overnight, info-control, 
        food, or summit. 
        """
        icons = { "control": "library",
                "overnight": "lodging",
                "info-control": "marker",
                "summit": "triangle",
                "food": "restaurant"
                }
        if len(row) < 4:
            row.append("")
        kind, lat, lon, title, desc = row
        if kind in icons:
            icon = icons[kind]
        else:
            icon = "marker"
        popup = f"{title}<br />{desc}"
        color = "#556b2f"
        self.landmarks.append(
            Landmark(kind, lat, lon, icon, title, desc, color))

    def attempt_load(self):
        handlers = {
            "event": self._row_event,
            "route": self._row_route,
            "spot": self._row_spot,
            "control": self._row_landmark,
            "summit": self._row_landmark,
            "info-control": self._row_landmark,
            "overnight": self._row_landmark,
            "food": self._row_landmark
            }
        path = "events/{}.csv".format(self.name)
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as csvfile:
                log.debug(f"Successfully opened '{path}' as CSV file")
                reader = csv.reader(csvfile)
                for row in reader:
                    log.debug(f"Processing row {row}")
                    if len(row) == 0:
                        continue
                    command = row[0].strip()
                    if command == "" or command.startswith("#"):
                        continue
                    # Content row. 
                    if command in handlers:
                        handler = handlers[command]
                        handler(row)
                    else:
                        log.debug(f"Didn't recognize commend {row}")
                        self.errmsg = f"Unrecognized command: {row}"
                        return
                if len(self.routes) > 0:
                    log.debug("Setting 'loaded' flag to True")
                    self.loaded = True
        except FileNotFoundError:
            self.errmsg = f"Unable to find information for event '{self.name}'"
            log.debug(f"File '{path}' not found")
        except Exception as e:
            log.debug(f"File parsing exception encountered: {e}")

    def route_is_defined(self, abbrev):
        for route in self.routes:
            if route.abbrev == abbrev:
                return True
        return False



def cli():
    """Command line args (for testing)"""
    parser = argparse.ArgumentParser("Test parsing the event configuration file")
    parser.add_argument("event", help="Name of the event; should match events/<eventname>.csv")
    args = parser.parse_args()
    return args

def main():
    """Test parsing an event configuration file"""
    args = cli()
    event = EventRecord(args.event)
    if event.loaded:
        print("Loaded successfully")
        print(f"Landmarks: {event.landmarks} ")
        print(f"Riders: {event.riders}")
    else:
        print("Event load failed")

if __name__ == "__main__":
    main()



