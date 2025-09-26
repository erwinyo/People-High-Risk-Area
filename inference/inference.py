# Built-in imports
import os
import sys
import uuid
import time
import json
import subprocess
import atexit
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor

# Third-party imports
import cv2
import schedule
import numpy as np
import supervision as sv
from loguru import logger
from ultralytics import YOLO
from vidgear.gears import CamGear, StreamGear


# Local imports
from utility import (
    get_epoch_ms_iso_utc,
    get_area,
    SynapsisResponse,
    upload_ndarray_to_minio,
    set_people_many,
    set_counts,
    get_timestamp_for_filename
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
    """
    AREA options:
        kepatihan           : depan_gerbang_masuk
        beringharjo         : penyeberangan_pasar
        nolkm               : area_1, area_2
        dewi_sartika        : area_1, area_2
        pedati_arah_gudang  : lorong_gudang
        pedati_surken       : lorong_pasar
    """

    SOURCES = {
        "kepatihan": "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8",
        "nolkm": "https://cctvjss.jogjakota.go.id/malioboro/NolKm_Utara.stream/playlist.m3u8",
        "beringharjo": "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8",
        "dewi_sartika": "https://restreamer3.kotabogor.go.id/memfs/b99d528a-1eb8-47bf-ba0f-a63fe11dbece.m3u8",
        "pedati_arah_gudang": "https://restreamer3.kotabogor.go.id/memfs/c2d90a44-8f2c-4103-82ad-6cb1730a5000.m3u8",
        "pedati_surken": "https://restreamer3.kotabogor.go.id/memfs/eedbb9a2-1571-41bd-92db-73b946e3e9b2.m3u8",
    }
    MINIO_BUCKET = "synapsis"
    PROGRAM_START_EPOCH_MS, PROGRAM_START_ISO_UTC = get_epoch_ms_iso_utc()

    # Start video stream
    stream = CamGear(source=SOURCES[LOCATION]).start()
    delay = int(1000 / stream.framerate)

    # Enable livestreaming
    stream_params = {
        "-input_framerate": int(stream.framerate),
        "-livestream": True,
        "-window_size": 2,
        "-extra_window_size": 2,
    }
    # describe a suitable manifest-file location/name
    output_folder = f"output/{get_timestamp_for_filename()}"
    os.makedirs(output_folder, exist_ok=True)
    streamer = StreamGear(
        output=f"{output_folder}/dash_out.mpd", format="dash", logging=True, **stream_params
    )

    # YOLO + Supervision setup
    model = YOLO(os.path.join("models", "yolo11l.pt"))
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

                    people_list.append(
                        {
                            "conf": float(confidence),
                            "bbox": [x1, y1, x2, y2],
                            "tracker_id": f"{PROGRAM_START_EPOCH_MS}_{tracker_id}",
                            "snapshot": presigned_url,
                        }
                    )

                if people_list == []:
                    logger.warning(
                        f"No people detected inside polygon zone of {area_name}"
                    )
                    continue
                # Insert people to MongoDB
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

    
        # Only show window if not running inside Docker
        if not os.path.exists("/.dockerenv"):
            cv2.imshow("view", annotated_image)
            if cv2.waitKey(delay) & 0xFF == ord("q"):
                break
        else:
            # send frame to streamer
            streamer.stream(annotated_image)
            cv2.waitKey(delay)

    cv2.destroyAllWindows()
    stream.stop()
    streamer.close()


if __name__ == "__main__":
    main()
