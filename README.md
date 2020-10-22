# Enroute (version 2)

Map locations of randonneurs with SPOT trackers.

Alternatives:  See SpotWalla, TrackLeaders, and the Spot tracking application used by
the Australian randonneurs for other takes on this basic theme.  Since SpotWalla in particular seems to be pretty good at filling the need for a general self-service tracker that can take both SPOT tracks and telephone-based tracking, my focus for further development will be specializing Enroute for randonneurs.

# Basic features

Display one or more spot checker locations (with a short "tail" of recent observations) along one or more mapped tracks.

# Additional features

## Done

*Distance on route*: Not the distance traveled, necessarily, but progress toward goal.  These can differ if the rider has taken some bonus miles.   Distance on route is based on the closest point on the mapped route, within a margin of 2km, provided the direction of travel is within 90 degrees of the direction of the route segment.  (The direction filter will usually cause out-and-back segments to be interpreted correctly.)

## Planned or under consideration

* Time in hand*, also known as *time in the bank*, is the difference between the time of observation and the closing time of an imaginary control at that point.

# What about event creation and registration?

Currently Enroute supports a simple self-service tracker creation for a single rider on a single route that is already pre-processed (with the ```prep''' script).  Something like this will probably be kept for simple, no fuss tracking of permanents.

A more elaborate process for group rides is under design, primarily by Michal Young and Lynne Fitzsimmons with additional design ideas by Adam Glass.
