# Built-in imports
import sys
import json
from datetime import datetime, timezone

# Third-party imports
import cv2
import numpy as np
import supervision as sv
from loguru import logger
from ultralytics import YOLO
from pymongo import MongoClient
from vidgear.gears import CamGear, VideoGear

# Local imports
from utility import get_epoch_ms_iso_utc, get_areas, set_or_update_area

# Logger configuration
logger.remove()
logger.add(sys.stdout, level="TRACE")


def main():
    SOURCE = "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8"

    # Start video stream
    stream = CamGear(source=SOURCE).start()
    cap = stream.stream
    fps = cap.get(cv2.CAP_PROP_FPS)

    model = YOLO("models\\yolo11l.pt")
    smoother = sv.DetectionsSmoother()
    box_annotator = sv.BoxAnnotator()
    label_annotator = sv.LabelAnnotator()
    trace_annotator = sv.TraceAnnotator()

    polygon = np.array([[735, 721], [1389, 682], [1757, 804], [891, 902]])
    polygon_zone = sv.PolygonZone(polygon=polygon)
    polygon_annotator = sv.PolygonZoneAnnotator(
        zone=polygon_zone, color=sv.Color.WHITE, thickness=2
    )

    while True:
        frame = stream.read()
        if frame is None:
            break
        epoch_ms, iso_utc = get_epoch_ms_iso_utc()

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
        detections = smoother.update_with_detections(detections)
        detections_inside = detections[polygon_zone.trigger(detections)]
        detections_inside_count = len(detections_inside)
        detections_outside = detections[~polygon_zone.trigger(detections)]
        detections_outside_count = len(detections_outside)

        labels = [f"{tracker_id}" for tracker_id in detections.tracker_id]
        annotated_image = polygon_annotator.annotate(
            scene=frame.copy(), label=f"{detections_inside_count}"
        )
        annotated_image = trace_annotator.annotate(annotated_image, detections)
        annotated_image = box_annotator.annotate(
            scene=annotated_image, detections=detections
        )
        annotated_image = label_annotator.annotate(
            scene=annotated_image, detections=detections, labels=labels
        )

        cv2.imshow("view", annotated_image)
        if cv2.waitKey(10) & 0xFF == ord("q"):
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
            set_or_update_area(
                config_value={
                    "name": area["name"],
                    "polygon_zone": area["polygon_zone"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
            )


def test_mongo():
    set_or_update_area(
        "area_1",
        {
            "name": "Main Entrance",
            "polygon_zone": [[735, 721], [1389, 682], [1757, 804], [891, 902]],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


if __name__ == "__main__":
    # main()
    # test_open_cv()
    # test_vidgear()
    # capture_frame()
    insert_area()
    # test_mongo()
