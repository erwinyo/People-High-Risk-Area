# Built-in imports


# Third-party imports
import cv2
import numpy as np
import supervision as sv
from ultralytics import YOLO
from vidgear.gears import CamGear

# Local imports


def main():
    SOURCE = "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8"
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
        zone=polygon_zone,
        color=sv.Color.WHITE,
        thickness=2
    )

    while True:
        frame = stream.read()
        if frame is None:
            break

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
        detections_inside_count = polygon_zone.current_count
        detections_outside = detections[~polygon_zone.trigger(detections)]

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
    cap = cv2.VideoCapture(
        "https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8",
        cv2.CAP_FFMPEG,
    )
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    ret, frame = cap.read()
    cap.release()
    if ret:
        cv2.imwrite("frame.jpg", frame)


if __name__ == "__main__":
    main()
    # test_open_cv()
    # test_vidgear()
    # capture_frame()
