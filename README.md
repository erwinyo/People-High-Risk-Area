# People-High-Risk-Area
Track and count people on high risk area

## Project Task List

| No | Task                        | Status | Notes / Issues                                                                 |
|----|-----------------------------|--------|--------------------------------------------------------------------------------|
| 1  | Database Setup              | [OK]    |                                                                                |
| 2  | Livestream Source           | [OK]    | find another city CCTV source, since the provided one is unstable during development |
| 3  | Object Detection & Tracking | [OK]    |                                                                                |
| 4  | Polygon Zone & Counting     | [OK]    |                                                                                |
| 5  | API Integration             | [OK]    |                                                                                |
| 6  | Containerization Deployment | [OK]    |                                                                                |
| 7  | Dashboard                   | [X]    |                                                                                |




## Demo

Insert gif or link to demo



**Challenge #2** Used Video
- https://cctvjss.jogjakota.go.id/malioboro/Malioboro_10_Kepatihan.stream/playlist.m3u8
- https://cctvjss.jogjakota.go.id/malioboro/Malioboro_30_Pasar_Beringharjo.stream/playlist.m3u8
- https://cctvjss.jogjakota.go.id/malioboro/NolKm_Utara.stream/playlist.m3u8
- https://restreamer3.kotabogor.go.id/memfs/eedbb9a2-1571-41bd-92db-73b946e3e9b2.m3u8
- https://restreamer3.kotabogor.go.id/memfs/b99d528a-1eb8-47bf-ba0f-a63fe11dbece.m3u8
- https://restreamer3.kotabogor.go.id/memfs/c2d90a44-8f2c-4103-82ad-6cb1730a5000.m3u8
## System Design
## Database Design## Requirements

You have to following already installed

- git
- docker 
- docker-compose

## Deployment

Clone this project

```bash
  git clone https://github.com/erwinyo/People-High-Risk-Area.git
```

Run docker compose up

```bash
  docker compose up -d --build
```


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