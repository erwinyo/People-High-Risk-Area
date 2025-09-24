# Built-in imports
import sys
import uuid
import time
import json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

# Third-party imports
import cv2
import schedule
import numpy as np
import supervision as sv
from loguru import logger
from ultralytics import YOLO
from pymongo import MongoClient
from vidgear.gears import CamGear, VideoGear

# Local imports
from utility import (
    MONGODB_URI,
    get_epoch_ms_iso_utc,
    get_timestamp,
    get_areas,
    update_area,
    set_area,
    get_area,
    SynapsisResponse,
    upload_ndarray_to_minio,
    set_people,
    set_people_many,
    set_people_bulk_write,
    set_counts,
)

# Logger configuration
logger.remove()
logger.add(sys.stdout, level="TRACE")


def refresh_areas(LOCATION, AREAS):
    area_ids, polygon_zones, polygon_annotators = [], [], []
    for area in AREAS:
        resp = get_area(location=LOCATION, area_name=area)
        logger.debug(f"Area response: {resp}")

        if resp == SynapsisResponse.NOT_FOUND:
            logger.warning(f"Area {area} not found in location {LOCATION}")
            return None, None, None
        if resp == SynapsisResponse.SERVER_ERROR:
            logger.error(f"Error retrieving area {area} in location {LOCATION}")
            return None, None, None
        id_temp = resp["_id"]
        area_ids.append(str(id_temp))

        p_temp = sv.PolygonZone(np.array(resp["polygon_zone"]))
        polygon_zones.append(p_temp)
        polygon_annotators.append(
            sv.PolygonZoneAnnotator(zone=p_temp, color=sv.Color.WHITE, thickness=2)
        )
    return area_ids, polygon_zones, polygon_annotators


def main():
    LOCATION = "kepatihan"
    AREAS = ["depan_gerbang_masuk"]
    SOURCES = {
        "kepatihan": "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8",
        "nolkm": "https://cctvjss.jogjakota.go.id/malioboro/NolKm_Utara.stream/playlist.m3u8",
        "beringharjo": "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8",
    }
    MINIO_BUCKET = "synapsis"
    PROGRAM_START_EPOCH_MS, PROGRAM_START_ISO_UTC = get_epoch_ms_iso_utc()

    # Start video stream
    stream = CamGear(source=SOURCES[LOCATION]).start()
    cap = stream.stream
    fps = cap.get(cv2.CAP_PROP_FPS)

    # YOLO + Supervision setup
    model = YOLO("models\\yolo11l.pt")
    tracker = sv.ByteTrack()
    smoother = sv.DetectionsSmoother()
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    trace_annotator = sv.TraceAnnotator()

    # Define polygon zone
    area_ids, polygon_zones, polygon_annotators = refresh_areas(LOCATION, AREAS)
    if area_ids is None and polygon_zones is None and polygon_annotators is None:
        logger.error("Error retrieving areas. Exiting...")
        return

    # Refresh areas trigger setup
    last_refresh_areas_time = time.time()
    refresh_areas_interval = 10  # seconds

    # Capture trigger setup
    last_capture_trigger_time = time.time()
    capture_trigger_interval = 5
    capture_trigger_flag = False
    while True:
        frame = stream.read()
        if frame is None:
            break

        # Inference
        result = model.track(
            source=frame,
            conf=0.45,
            classes=[0],
            persist=True,
            tracker="bytetrack.yaml",
            device=0,
            verbose=False,
        )[0]
        detections = sv.Detections.from_ultralytics(result)
        detections = tracker.update_with_detections(detections)
        detections = smoother.update_with_detections(detections)

        current_time = time.time()
        # Capture trigger
        if current_time - last_capture_trigger_time >= capture_trigger_interval:
            capture_trigger_flag = True
            logger.info(
                f"Triggered event at {capture_trigger_interval} second interval"
            )
            last_capture_trigger_time = current_time
        # Refresh areas trigger
        if current_time - last_refresh_areas_time >= refresh_areas_interval:
            area_ids, polygon_zones, polygon_annotators = refresh_areas(LOCATION, AREAS)
            logger.info(f"Refreshing areas at {refresh_areas_interval} second interval")
            last_refresh_areas_time = current_time

        annotated_image = frame.copy()
        for area_id, area_name, polygon_zone, polygon_annotator in zip(
            area_ids, AREAS, polygon_zones, polygon_annotators
        ):
            polygon_trigger = polygon_zone.trigger(detections)
            detections_inside = detections[polygon_trigger]
            detections_inside_count = len(detections_inside)
            detections_outside = detections[~polygon_trigger]
            detections_outside_count = len(detections_outside)

            annotated_image = polygon_annotator.annotate(
                scene=annotated_image, label=f"{area_name}: {detections_inside_count}"
            )

            # trigger event for capture people inside polygon zone
            if capture_trigger_flag:
                st_ = time.time()

                people_list = []
                cropped_images = []
                if detections.is_empty():
                    continue
                for (
                    xyxy,
                    mask,
                    confidence,
                    class_id,
                    tracker_id,
                    data,
                ) in detections:
                    x1, y1, x2, y2 = map(int, xyxy)

                    # Upload snapshot to MinIO
                    presigned_url = upload_ndarray_to_minio(
                        object_name=f"{MINIO_BUCKET}/{LOCATION}/{area_name}/{uuid.uuid4()}.jpg",
                        ndarray_image=cv2.cvtColor(
                            sv.crop_image(image=frame, xyxy=[x1, y1, x2, y2]),
                            cv2.COLOR_BGR2RGB,
                        ),
                    )

                    cropped_images

                    people_list.append(
                        {
                            "conf": float(confidence),
                            "bbox": [x1, y1, x2, y2],
                            "tracker_id": f"{PROGRAM_START_EPOCH_MS}_{tracker_id}",
                            "snapshot": presigned_url,
                        }
                    )

                    # inserted_id = set_people(
                    #     conf=float(confidence),
                    #     bbox=[x1, y1, x2, y2],
                    #     tracker_id=f"{PROGRAM_START_EPOCH_MS}_{tracker_id}",
                    #     snapshot=presigned_url,
                    # )

                # Insert people to MongoDB
                # set_people_bulk_write(people_list, ordered=False)
                inserted_ids = set_people_many(people_list)
                if inserted_ids == SynapsisResponse.SERVER_ERROR:
                    logger.error("Error inserting people to database")
                    return
                inserted_ids = np.array(inserted_ids).astype(str)

                set_counts(
                    area_id=area_id,
                    in_num=detections_inside_count,
                    out_num=detections_outside_count,
                    in_people_id=inserted_ids[polygon_trigger].tolist(),
                    out_people_id=inserted_ids[~polygon_trigger].tolist(),
                    in_people_tracker_id=[
                        f"{PROGRAM_START_EPOCH_MS}_{tracker_id}"
                        for tracker_id in detections_inside.tracker_id
                    ],
                    out_people_tracker_id=[
                        f"{PROGRAM_START_EPOCH_MS}_{tracker_id}"
                        for tracker_id in detections_outside.tracker_id
                    ],
                )

                en = time.time()
                logger.debug(f"Set people and counts time: {en - st_} seconds")

        capture_trigger_flag = False

        labels = [f"#{tracker_id}" for tracker_id in detections.tracker_id]
        annotated_image = trace_annotator.annotate(annotated_image, detections)
        annotated_image = box_annotator.annotate(
            scene=annotated_image, detections=detections
        )
        annotated_image = label_annotator.annotate(
            scene=annotated_image, detections=detections, labels=labels
        )

        cv2.imshow("view", annotated_image)
        if cv2.waitKey(5) & 0xFF == ord("q"):
            break


def test_open_cv():
    cap = cv2.VideoCapture(
        "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8",
        cv2.CAP_FFMPEG,
    )
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    while True:
        ret, frame = cap.read()
        print(ret)
        cv2.imshow("frame", frame)
        if cv2.waitKey(30) & 0xFF == ord("q"):
            break
    cap.release()
    cv2.destroyAllWindows()


def test_vidgear():
    # open any valid video stream(for e.g `myvideo.avi` file)
    stream = VideoGear(
        source="https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8"
    ).start()

    # loop over
    while True:

        # read frames from stream
        frame = stream.read()

        # check for frame if Nonetype
        if frame is None:
            break

        # {do something with the frame here}

        # Show output window
        cv2.imshow("Output Frame", frame)

        # check for 'q' key if pressed
        key = cv2.waitKey(30) & 0xFF
        if key == ord("q"):
            break

    # close output window
    cv2.destroyAllWindows()

    # safely close video stream
    stream.stop()


def capture_frame():
    # cap = cv2.VideoCapture(
    #     "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8",
    #     cv2.CAP_FFMPEG,
    # )

    cap = cv2.VideoCapture(
        "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8",
        cv2.CAP_FFMPEG,
    )

    # cap = cv2.VideoCapture(
    #     "https://cctvjss.jogjakota.go.id/malioboro/NolKm_Utara.stream/playlist.m3u8",
    #     cv2.CAP_FFMPEG,
    # )

    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite("frame.jpg", frame)


def insert_area():
    with open("areas.json", "r") as f:
        area_data = json.load(f)
    for location, areas in area_data.items():
        for area in areas:
            logger.info(f"Inserting area: {location}_{area['name']}")
            set_area(
                {
                    "location": location,
                    "area_name": area["name"],
                    "polygon_zone": area["polygon_zone"],
                    "updated_at": get_timestamp(),
                }
            )


def test_mongo():
    LOCATION = "kepatihan"
    AREAS = "depan_gedung_baru"

    # set_area(
    #     {
    #         "location": LOCATION,
    #         "area_name": AREAS,
    #         "polygon_zone": [[891, 902], [1757, 804], [2000, 850], [1000, 950]],
    #         "updated_at": get_timestamp(),
    #     }
    # )

    # update_area(
    #     location=LOCATION,
    #     area_name=AREAS,
    #     config_value={
    #         "polygon_zone": [[1000, 902], [1000, 804], [2000, 850], [1000, 950]],
    #         "updated_at": get_timestamp(),
    #     },
    # )

    # logger.debug(get_areas())
    MONGODB_URI = "mongodb://admin:admin@localhost:27017"
    mo_client = MongoClient(MONGODB_URI)
    mo_synapsis_people = mo_client["synapsis"]["people"]
    count = mo_synapsis_people.count_documents({"tracker_id": "1758646608497_1"})
    logger.info(f"Count: {count}")


def test_minio():
    upload_ndarray_to_minio(
        object_name="synapsis/kepatihan/test-ndarray.jpg",
        ndarray_image=np.zeros((100, 100, 3), dtype=np.uint8),
    )


if __name__ == "__main__":
    main()
    # test_open_cv()
    # test_vidgear()
    # capture_frame()
    # insert_area()
    # test_mongo()
    # test_minio()
