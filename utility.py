# Built-in imports
import time
from enum import Enum
from io import BytesIO
from bson import ObjectId
from datetime import datetime, timezone, timedelta

# Third-party imports
from PIL import Image
from minio import Minio
from loguru import logger
from pymongo import MongoClient
from minio.error import S3Error
from minio.commonconfig import CopySource

# Local imports


class SynapsisResponse(Enum):
    NOT_FOUND = "Resource not found"
    UNAUTHORIZED = "Unauthorized access"
    BAD_REQUEST = "Bad request"
    INVALID_INPUT = "Invalid input"
    SERVER_ERROR = "Internal server error"
    FORBIDDEN = "Forbidden"
    SUCCESS = "Operation completed successfully"


# MongoDB setup
MONGODB_URI = "mongodb://admin:admin@localhost:27017"
mo_client = MongoClient(MONGODB_URI)
mo_synapsis_people = mo_client["synapsis"]["people"]
mo_synapsis_areas = mo_client["synapsis"]["areas"]
mo_synapsis_counts = mo_client["synapsis"]["counts"]

# MinIO setup
MINIO_URI = "localhost:9000"
MINIO_SECURE = False
MINIO_ACCESS_KEY = "minioadmin"
MINIO_SECRET = "minioadmin"
minio_client = Minio(
    MINIO_URI,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET,
    secure=MINIO_SECURE,
)


def get_epoch_ms_iso_utc():
    # Epoch timestamp (milliseconds)
    epoch_ms = int(time.time() * 1000)

    # ISO 8601 UTC timestamp
    iso_utc = datetime.now(timezone.utc).isoformat()

    return epoch_ms, iso_utc


# ============================================================


def update_area(location, area_name, config_value):
    """Set or update an area in the database.

    Args:
        location (str): The location of the area.
        area_name (str): The name of the area to update.
        config_value (dict): The configuration values to set.
            example:
            location = "kepatihan"
            area_name = "depan_gedung"
            config_value = {
                "polygon_zone": [[735, 721], [1389, 682], [1757, 804], [891, 902]],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    """
    query_filter = {"location": location, "area_name": area_name}
    update_operation = {"$set": config_value}
    try:
        mo_synapsis_areas.update_one(
            query_filter,
            update_operation,
            upsert=True,
        )
        logger.info(f"Area updated: `{area_name}` at location `{location}`")
        logger.debug(f"Area details: {config_value}")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.error(f"Error updating area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def set_area(config_value):
    """Set or update an area in the database.

    Args:
        config_value (dict): The configuration values to set.
            example:
            config_value = {
                "_id": ObjectId("650d3f4e1c9d440000f8b2a1"),
                "location": "kepatihan",
                "area_name": "depan_gedung",
                "polygon_zone": [[735, 721], [1389, 682], [1757, 804], [891, 902]],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
    """
    try:
        mo_synapsis_areas.insert_one(config_value)
        logger.info(
            f"Area inserted: `{config_value.get('area_name')}` at location `{config_value.get('location')}`"
        )
        logger.debug(f"Area details: {config_value}")

        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.debug(f"Error inserting area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def get_area(location, area_name):
    """Get an area from the database.

    Args:
        location (str): The location of the area.
        area_name (str): The name of the area.
    Returns:
        dict: The area details or an error response.
    """

    try:
        area = mo_synapsis_areas.find_one(
            {"location": location, "area_name": area_name}, {"_id": 0}
        )
        logger.debug(f"Retrieved area: {area}")
        if area is None:
            return SynapsisResponse.NOT_FOUND
        return area
    except Exception as e:
        logger.debug(f"Error retrieving area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def get_areas():
    return list(mo_synapsis_areas.find({}, {"_id": 0}))


# ============================================================


def get_count_by_tracker_id(tracker_id):
    logger.debug(f"Getting count for tracker_id: {tracker_id}")
    count = mo_synapsis_people.count_documents({"tracker_id": tracker_id})
    return count


def set_counts(
    area_id,
    in_num,
    out_num,
    in_people_id,
    out_people_id,
    in_people_tracker_id,
    out_people_tracker_id,
):
    counts_by_tracker_id = {}
    for tracker_id in in_people_tracker_id:
        counts_by_tracker_id[tracker_id] = get_count_by_tracker_id(tracker_id)
    try:
        mo_synapsis_people.insert_one(
            {
                "area_id": area_id,
                "in": in_num,
                "out": out_num,
                "in_people_id": in_people_id,
                "out_people_id": out_people_id,
                "in_people_tracker_id": in_people_tracker_id,
                "out_people_tracker_id": out_people_tracker_id,
                "in_people_occurrences": counts_by_tracker_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        logger.debug(f"Counts updated for area_id: {area_id}")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.debug(f"Error updating counts: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


# ============================================================


def set_people(conf, bbox, tracker_id, snapshot):
    try:
        result = mo_synapsis_people.insert_one(
            {
                "conf": conf,
                "bbox": bbox,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "tracker_id": tracker_id,
                "snapshot": snapshot,
            }
        )
        logger.debug(f"People inserted with id: {result.inserted_id}")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.debug(f"Error inserting people: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


# ============================================================


def upload_ndarray_to_minio(object_name, ndarray_image, fmt="JPEG"):
    try:
        if "/" not in object_name:
            raise ValueError(
                "object_name must be in format '<bucket>/<path/to/object>'"
            )

        bucket_name, object_name = object_name.split("/", 1)

        # Convert ndarray to bytes
        image_bytes = BytesIO()
        Image.fromarray(ndarray_image).save(image_bytes, format=fmt)
        image_bytes.seek(0)
        size = image_bytes.getbuffer().nbytes

        # Upload image to MinIO
        minio_client.put_object(
            bucket_name,
            object_name,
            image_bytes,
            size,
            content_type=f"image/{fmt.lower()}",
        )

        presigned_url = minio_client.presigned_get_object(
            bucket_name, object_name, expires=timedelta(days=7)
        )

        return presigned_url

    except S3Error as e:
        logger.error(f"Failed to upload image to MinIO: {e}", exc_info=True)
        return SynapsisResponse.SERVER_ERROR
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return SynapsisResponse.SERVER_ERROR
