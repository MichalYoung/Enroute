"""
Read spreadsheet (which may be uploaded) with device assignments.
Soon:  Copy to MongoDB databasse.
"""

from openpyxl import Workbook
from openpyxl import load_workbook



# Configured variables
import config
from pymongo import MongoClient
MONGO_URL = config.get("mongo_url")

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
collection = db.devices   # TrackLeaders tracks


def read_assignments(filename):
    """Read spot device assignments from spreadsheet.
    filename should be path to an Excel workbook.
    """
    personal_spots = [ ]
    trackleaders_spots = [ ]
    support_spots = [ ]
    wb = load_workbook(filename)
    sheet = wb.active
    for row in sheet.rows:
        tag = row[0].value
        if tag == "TL":
            # TrackLeader rented spot
            record = { "rider": (row[2].value or "_") + " " + (row[3].value or "_"),
                       "esn": row[4].value,
                       "unit": row[1].value
                       }
            trackleaders_spots.append(record)
        elif tag == "PS" or tag == "SV":
            # Personal spot; we have a URL
            url = row[4].value
            gid  = url.split("=")[-1]
            record = { "rider": (row[2].value or "_") + " " + (row[3].value or "_"),
            "gid": gid
            }
            if tag == "PS":
                personal_spots.append(record)
            elif tag == "SV":
                support_spots.append(record)
                assignments = {"kind": "assignments",
                    "personal_spots": personal_spots,
                   "trackleaders_spots": trackleaders_spots,
                   "support_spots": support_spots
                   }
    return assignments

def save_assignments(assignments: dict):
    """Save configuration in database"""
    collection.replace_one({"kind": "assignments"}, assignments, upsert=True)

def get_assignments() -> dict:
    """Get configuration from database"""
    assignments = collection.find_one({"kind": "assignments"})
    return assignments


if __name__ == "__main__":
    assignments = read_assignments("SPOT_assignments.xlsx")
    save_assignments(assignments)

