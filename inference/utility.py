# Built-in imports
import re
import os
import time
from enum import Enum
from io import BytesIO
from bson import ObjectId
from dateutil import parser as _dateutil_parser
from datetime import datetime, timezone, timedelta

# Third-party imports
from PIL import Image
from minio import Minio
from loguru import logger
from dotenv import load_dotenv
from pymongo import MongoClient
from minio.error import S3Error
from minio.commonconfig import CopySource

# Local imports


load_dotenv()


class SynapsisResponse(Enum):
    NOT_FOUND = "Resource not found"
    UNAUTHORIZED = "Unauthorized access"
    BAD_REQUEST = "Bad request"
    INVALID_INPUT = "Invalid input"
    SERVER_ERROR = "Internal server error"
    FORBIDDEN = "Forbidden"
    SUCCESS = "Operation completed successfully"


# MongoDB setup
MONGODB_URI = os.getenv("MONGODB_URI")
mo_client = MongoClient(MONGODB_URI)
mo_synapsis_people = mo_client["synapsis"]["people"]
mo_synapsis_areas = mo_client["synapsis"]["areas"]
mo_synapsis_counts = mo_client["synapsis"]["counts"]

# MinIO setup
MINIO_URI = os.getenv("MINIO_URI")
MINIO_SECURE = os.getenv("MINIO_SECURE") == "True"
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY")
MINIO_SECRET = os.getenv("MINIO_SECRET")
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
    iso_utc = get_timestamp()
    return epoch_ms, iso_utc


def get_timestamp():
    now_utc = datetime.now(timezone.utc)
    return now_utc


def get_timestamp_for_filename():
    # WIB timezone (UTC+7) Indonesia Western Standard Time
    WIB = timezone(timedelta(hours=7))
    now_wib = datetime.now(WIB).strftime("%Y%m%d_%H%M%S")
    return now_wib


# ============================================================
# AREAS


def get_area_names_based_on_location(location):
    areas = list(mo_synapsis_areas.find({"location": location}))
    areas = [area["area_name"] for area in areas]
    return areas


def check_area_exists(location, area_name):
    query_filter = {"location": location, "area_name": area_name}
    return mo_synapsis_areas.count_documents(query_filter) > 0


def delete_area(location, area_name):
    """Delete an area from the database.

    Args:
        location (str): The location of the area.
        area_name (str): The name of the area to delete.
    """
    if not check_area_exists(location, area_name):
        logger.warning(f"Area not found: `{area_name}` at location `{location}`")
        return SynapsisResponse.NOT_FOUND

    query_filter = {"location": location, "area_name": area_name}
    try:
        mo_synapsis_areas.delete_one(query_filter)
        logger.info(f"Area deleted: `{area_name}` at location `{location}`")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.error(f"Error deleting area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def update_area(location, area_name, polygon_zone):
    """Set or update an area in the database.

    Args:
        location (str): The location of the area.
        area_name (str): The name of the area to update.
        polygon_zone (list): The polygon zone coordinates.
            example:
            location = "kepatihan"
            area_name = "depan_gedung"
            polygon_zone = [[735, 721], [1389, 682], [1757, 804], [891, 902]]
    """
    if not check_area_exists(location, area_name):
        logger.warning(f"Area not found: `{area_name}` at location `{location}`")
        return SynapsisResponse.NOT_FOUND

    query_filter = {"location": location, "area_name": area_name}
    update_operation = {"$set": {"polygon_zone": polygon_zone}}
    try:
        mo_synapsis_areas.update_one(
            query_filter,
            update_operation,
            upsert=True,
        )
        logger.info(f"Area updated: `{area_name}` at location `{location}`")
        logger.debug(f"Updated polygon_zone: {polygon_zone}")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.error(f"Error updating area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def set_area(location, area_name, polygon_zone):
    """Set or update an area in the database.

    Args:
        location (str): The location of the area.
        area_name (str): The name of the area to set.
        polygon_zone (list): The polygon zone coordinates.
            example:
            location = "kepatihan"
            area_name = "depan_gedung"
            polygon_zone = [[735, 721], [1389, 682], [1757, 804], [891, 902]]
    Returns:
        SynapsisResponse: SUCCESS, BAD_REQUEST, or SERVER_ERROR
    """
    if check_area_exists(location, area_name):
        logger.warning(f"Area already exists: `{area_name}` at location `{location}`")
        return SynapsisResponse.BAD_REQUEST

    try:
        mo_synapsis_areas.insert_one(
            {
                "location": location,
                "area_name": area_name,
                "polygon_zone": polygon_zone,
                "updated_at": get_timestamp(),
            }
        )
        logger.info(f"Area set: `{area_name}` at location `{location}`")
        logger.debug(f"Polygon_zone: {polygon_zone}")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.error(f"Error inserting area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def get_area(location, area_name):
    """Get an area from the database.

    Args:
        location (str): The location of the area.
        area_name (str): The name of the area.
    Returns:
        dict: The area details or an error response.
    """
    if not check_area_exists(location, area_name):
        logger.warning(f"Area not found: `{area_name}` at location `{location}`")
        return SynapsisResponse.NOT_FOUND
    try:
        area = mo_synapsis_areas.find_one(
            {"location": location, "area_name": area_name}
        )
        logger.debug(f"Retrieved area: {area}")
        if area is None:
            return SynapsisResponse.NOT_FOUND
        return area
    except Exception as e:
        logger.error(f"Error retrieving area: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def get_areas():
    """Get all areas from the database."""
    return list(mo_synapsis_areas.find({}, {"_id": 0}))


# ============================================================
# COUNTS


def get_count_live():
    """Get the latest count from the database.

    Returns:
        dict: The latest count data
    """
    try:
        doc = mo_synapsis_counts.find_one(sort=[("timestamp", -1)])
        if doc:
            doc["_id"] = str(doc["_id"])
            return doc
    except Exception as e:
        logger.error(f"Error retrieving latest counts: {str(e)}")
        return SynapsisResponse.NOT_FOUND


# Then reuse the get_count from earlier but keep the improved normalization:
def get_count(
    start_time: str = None, end_time: str = None, page: str = "10", limit: str = "10"
):
    # Converted to int
    start_time = int(start_time)
    end_time = int(end_time)
    page = int(page)
    limit = int(limit)

    query = {}
    ts_query = {}
    if start_time is not None:
        ts_query["$gte"] = datetime.fromtimestamp(start_time)
    if end_time is not None:
        ts_query["$lte"] = datetime.fromtimestamp(end_time)
    if ts_query:
        query["timestamp"] = ts_query

    skip = (page - 1) * limit

    try:
        cursor = (
            mo_synapsis_counts.find(query).skip(skip).limit(limit).sort("timestamp", -1)
        )
        data = list(cursor)
        for d in data:
            d["_id"] = str(d["_id"])
        total_in = sum(d.get("in", 0) for d in data)
        total_out = sum(d.get("out", 0) for d in data)

        total_records = mo_synapsis_counts.count_documents(query)
        logger.debug(
            f"Retrieved counts: page={page}, limit={limit}, total_records={total_records}, query={query}"
        )
        return {
            "page": page,
            "limit": limit,
            "total_in": total_in,
            "total_out": total_out,
            "total_records": total_records,
            "data": data,
        }
    except Exception as e:
        logger.error(f"Error retrieving counts: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def get_count_by_tracker_id(tracker_id):
    """Get count data for a specific tracker ID.

    Args:
        tracker_id (str): The ID of the tracker.
    Returns:
        int: The count of occurrences for the given tracker ID.
    """
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
    """
    Insert a count record into the database.
    Args:
        area_id (str): The ID of the area.
        in_num (int): Number of people detected entering the area.
        out_num (int): Number of people detected exiting the area.
        in_people_id (list of str): List of IDs of people who entered.
        out_people_id (list of str): List of IDs of people who exited.
        in_people_tracker_id (list of str): List of tracker IDs for people who entered.
        out_people_tracker_id (list of str): List of tracker IDs for people who exited.
    Returns:
        SynapsisResponse: SUCCESS or SERVER_ERROR
    """
    counts_by_tracker_id = {}
    for tracker_id in in_people_tracker_id:
        counts_by_tracker_id[f"{tracker_id}"] = get_count_by_tracker_id(tracker_id)
    try:
        mo_synapsis_counts.insert_one(
            {
                "area_id": area_id,
                "in": in_num,
                "out": out_num,
                "in_people_id": in_people_id,
                "out_people_id": out_people_id,
                "in_people_tracker_id": in_people_tracker_id,
                "out_people_tracker_id": out_people_tracker_id,
                "in_people_occurrences": counts_by_tracker_id,
                "timestamp": get_timestamp(),
            }
        )
        logger.debug(f"Counts updated for area_id: {area_id}")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.error(f"Error updating counts: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


# ============================================================
# PEOPLE


def set_people(conf, bbox, tracker_id, snapshot):
    """Insert a single person record into the database.
    Args:
        conf (float): Confidence score of the detection.
        bbox (list): Bounding box coordinates [x1, y1, x2, y2].
        tracker_id (str): Unique tracker ID for the person.
        snapshot (str): URL to the snapshot image.

    Returns:
        ObjectId: The ID of the inserted record or SynapsisResponse.SERVER_ERROR on failure
    """
    try:
        result = mo_synapsis_people.insert_one(
            {
                "conf": conf,
                "bbox": bbox,
                "timestamp": get_timestamp(),
                "tracker_id": tracker_id,
                "snapshot": snapshot,
            }
        )
        logger.debug(f"People inserted with id: {result.inserted_id}")
        return result.inserted_id
    except Exception as e:
        logger.error(f"Error inserting people: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def set_people_many(people_list):
    """
    Insert multiple people records into the database.

    Args:
        people_list (list of dict): Each dict should contain keys:
            'conf', 'bbox', 'tracker_id', 'snapshot'.
            Example:
            [
                {
                    "conf": 0.98,
                    "bbox": [100, 200, 300, 400],
                    "tracker_id": "abc123",
                    "snapshot": "http://example.com/snapshot1.jpg"
                },
                ...
            ]
    """
    try:
        # Add timestamp to each record
        timestamp = get_timestamp()
        for person in people_list:
            person["timestamp"] = timestamp
        result = mo_synapsis_people.insert_many(people_list)
        logger.debug(f"People inserted with ids: {result.inserted_ids}")
        return result.inserted_ids
    except Exception as e:
        logger.error(f"Error inserting people: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


def set_people_bulk_write(people_list, ordered=False):
    """Insert multiple people records into the database.

    Args:
        people_list (list of dict): Each dict should contain keys:
            'conf', 'bbox', 'tracker_id', 'snapshot'.
            Example:
            [
                {
                    "conf": 0.98,
                    "bbox": [100, 200, 300, 400],
                    "tracker_id": "abc123",
                    "snapshot": "http://example.com/snapshot1.jpg"
                },
                ...
            ]
        ordered (bool): Whether the inserts should be ordered. Defaults to False.
    """
    try:
        # Add timestamp to each record
        timestamp = get_timestamp()
        for person in people_list:
            person["timestamp"] = timestamp
        requests = [mo_synapsis_people.insert_one(i) for i in people_list]
        mo_synapsis_people.bulk_write(requests, ordered=ordered)
        logger.debug(f"People bulk inserted: {len(people_list)} records")
        return SynapsisResponse.SUCCESS
    except Exception as e:
        logger.error(f"Error in bulk inserting people: {str(e)}")
        return SynapsisResponse.SERVER_ERROR


# ============================================================
# MINIO


def upload_ndarray_to_minio(object_name, ndarray_image, expire_days=7, fmt="JPEG"):
    """Upload a NumPy ndarray image to MinIO.
    Args:
        object_name (str): The object name in MinIO, including bucket and path.
        ndarray_image (np.ndarray): The image as a NumPy ndarray.
        expire_days (int, optional): URL expiration in days. Defaults to 7.
        fmt (str, optional): Image format (e.g., 'JPEG', 'PNG'). Defaults to 'JPEG'.
    Returns:
        str: Presigned URL of the uploaded image or SynapsisResponse.SERVER_ERROR on failure
    """
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
            bucket_name, object_name, expires=timedelta(days=expire_days)
        )

        return presigned_url

    except S3Error as e:
        logger.error(f"Failed to upload image to MinIO: {e}", exc_info=True)
        return SynapsisResponse.SERVER_ERROR
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return SynapsisResponse.SERVER_ERROR
