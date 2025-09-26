# People-High-Risk-Area
High-Risk Area People Counting systems are designed to automatically monitor and count the number of individuals within designated zones using computer vision and machine learning techniques. These systems help enhance safety by detecting overcrowding in vulnerable areas, providing real-time insights, and supporting authorities in managing risks more efficiently.

## Project Task List

| No | Task                        | Status | Notes / Issues                                                                 |
|----|-----------------------------|--------|--------------------------------------------------------------------------------|
| 1  | Database Setup              | [OK]    |                                                                                |
| 2  | Livestream Source           | [OK]    | |
| 3  | Object Detection & Tracking | [OK]    |                                                                                |
| 4  | Polygon Zone & Counting     | [OK]    |                                                                                |
| 5  | API Integration             | [OK]    |                                                                                |
| 6  | Docker Deployment | [OK]    |                                                                                |
| 7  | Dashboard                   | [X]    |                                                                                |




## Demo

[![Watch the video](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/thumbnail.png)](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/demo.mp4)


Livestream Video
- https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8 (default)
- https://cctvjss.jogjakota.go.id/malioboro/NolKm_Utara.stream/playlist.m3u8
- https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8
- https://restreamer3.kotabogor.go.id/memfs/b99d528a-1eb8-47bf-ba0f-a63fe11dbece.m3u8
- https://restreamer3.kotabogor.go.id/memfs/c2d90a44-8f2c-4103-82ad-6cb1730a5000.m3u8
- https://restreamer3.kotabogor.go.id/memfs/eedbb9a2-1571-41bd-92db-73b946e3e9b2.m3u8

If you want to change the source, below is the code location (inference/inference.py)

![Video Source Code](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/video_source_code.png)

## System Design

![System Design](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/system_design.png)

- **"Area Update Interval Triggered?"**: It request updated data from database if any changes present (create, delete, update)
- **"Snap Interval Triggered?"**: It send captured scene (people inside and outside of area) been snapshot and registered on database
- **"Want Change Area?"**: It request an update of area and registered to database
- **"Want Status Count?"**: It request history or live status count



### Tech Stack
- Minio
- MongoDB
- YOLOv11
- Supervision
- Docker
- FastAPI
- OpenCV
## Database Design

**Below is the list of structure of collection on MongoDB:**

Areas
![Areas collection](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/db_areas.png)


Peoples
![Peoples collection](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/db_peoples.png)


Counts
![Counts collection](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/db_counts.png)
## Docker Deployment

You have to following already installed

- git
- docker & docker-compose (https://docs.docker.com/engine/install/)

Clone this project

```bash
git clone https://github.com/erwinyo/People-High-Risk-Area.git
```

Run docker compose up

```bash
docker compose -f docker-compose.yml up -d --build
```


Run .mpd file on the **output/** folder
- Open VLC media player
- Click media, choose open file
- Open .mpd file
*Note: the result is playable, but sometime lagging and stopped. Need refresh periodically.
## Manual Deployment

You have to following already installed

- git
- uv (https://docs.astral.sh/uv/getting-started/installation)


Clone this project

```bash
git clone https://github.com/erwinyo/People-High-Risk-Area.git
```

Deploy MongoDB and Minio Containers

```bash
docker compose -f docker-compose-manual.yml up -d --build
```

Run API

```bash
cd api
uv run python api.py
```

Run Inference

```bash
cd inference
uv run python inference.py
```

A window will be pop-up to show the inference

## API Reference

#### Get counts status 

```http
  GET /api/stats
```

| Name       | Type | Required | Default | Description                                  |
|------------|------|----------|---------|----------------------------------------------|
| start_time | int  | No       | None    | Start timestamp (epoch) for filtering stats. |
| end_time   | int  | No       | None    | End timestamp (epoch) for filtering stats.   |
| page       | int  | No       | 1       | Page number for paginated results.           |
| limit      | int  | No       | 10      | Number of items per page.                    |


#### Get live count status 

```http
  GET /api/stats/live
```


#### Get all area 

```http
  GET /api/area
```

#### Create new area 

```http
  POST /api/set/area
```

| Field        | Type            | Required | Description                              |
|--------------|-----------------|----------|------------------------------------------|
| location     | str             | Yes      | The location identifier.                  |
| area_name    | str             | Yes      | The name of the area.                     |
| polygon_zone | list[list[int]] | Yes      | Polygon coordinates defining the zone.    |



```http
  POST /api/get/area
```

| Field     | Type | Required | Description               |
|-----------|------|----------|---------------------------|
| location  | str  | Yes      | The location identifier.  |
| area_name | str  | Yes      | The name of the area.     |


```http
  POST /api/update/area
```

| Field        | Type            | Required | Description                              |
|--------------|-----------------|----------|------------------------------------------|
| location     | str             | Yes      | The location identifier.                  |
| area_name    | str             | Yes      | The name of the area.                     |
| polygon_zone | list[list[int]] | Yes      | Updated polygon coordinates for the zone. |



```http
  POST /api/delete/area
```

| Field     | Type | Required | Description               |
|-----------|------|----------|---------------------------|
| location  | str  | Yes      | The location identifier.  |
| area_name | str  | Yes      | The name of the area.     |

## Screenshots

![Snap1](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/snap1.png)

![Snap2](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/snap2.png)

![Snap3](https://raw.githubusercontent.com/erwinyo/People-High-Risk-Area/refs/heads/main/media/snap3.png)

