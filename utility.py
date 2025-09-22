# Built-in imports
import time
from bson import ObjectId
from datetime import datetime, timezone

# Third-party imports
from pymongo import MongoClient

# Local imports

MONGODB_URI = "mongodb://admin:admin@localhost:27017"
mo_client = MongoClient(MONGODB_URI)
mo_synapsis_people = mo_client["synapsis"]["people"]
mo_synapsis_areas = mo_client["synapsis"]["areas"]
mo_synapsis_counts = mo_client["synapsis"]["counts"]


def get_epoch_ms_iso_utc():
    # Epoch timestamp (milliseconds)
    epoch_ms = int(time.time() * 1000)

    # ISO 8601 UTC timestamp
    iso_utc = datetime.now(timezone.utc).isoformat()

    return epoch_ms, iso_utc


def set_or_update_area(config_value, area_id=ObjectId()):
    """Set or update an area in the database.

    Args:
        area_id (str): The ID of the area to update.
        config_value (dict): The configuration values to set.
            example:
            config_value = {
                "name": "Main Entrance",
                "polygon_zone": [[735, 721], [1389, 682], [1757, 804], [891, 902]],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    """
    query_filter = {"_id": area_id}
    update_operation = {"$set": config_value}
    mo_synapsis_areas.update_one(
        query_filter,
        update_operation,
        upsert=True,
    )


def get_areas():
    areas = list(mo_synapsis_areas.find({}, {"_id": 0}))
    return areas
