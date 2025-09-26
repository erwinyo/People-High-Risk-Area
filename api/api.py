# Built-in imports
from datetime import datetime, timezone

# Third-party imports
import uvicorn
from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import FastAPI, Body

# Local imports
from utility import (
    SynapsisResponse,
    get_areas,
    update_area,
    set_area,
    get_area,
    get_count_live,
    get_count,
    delete_area,
)


class SetAreaRequest(BaseModel):
    location: str
    area_name: str
    polygon_zone: list[list[int]]


class GetAreaRequest(BaseModel):
    location: str
    area_name: str


class UpdateAreaRequest(BaseModel):
    location: str
    area_name: str
    polygon_zone: list[list[int]]


class DeleteAreaRequest(BaseModel):
    location: str
    area_name: str


app = FastAPI()


@app.get("/api/stats", tags=["status"])
async def fastapi_get_stats(
    start_time: str = None, end_time: str = None, page: int = 1, limit: int = 10
):
    resp = get_count(start_time=start_time, end_time=end_time, page=page, limit=limit)
    if resp == SynapsisResponse.SERVER_ERROR:
        return {"status": "error", "message": "Error retrieving stats"}
    else:
        return {
            "status": "success",
            "message": "Stats retrieved successfully",
            "data": resp,
        }


@app.get("/api/stats/live", tags=["status"])
def get_latest_stats():
    resp = get_count_live()
    if resp == SynapsisResponse.SERVER_ERROR:
        return {"status": "error", "message": "Error retrieving latest stats"}
    else:
        return {
            "status": "success",
            "message": "Latest stats retrieved successfully",
            "data": resp,
        }


@app.get("/api/area", tags=["area"])
async def fastapi_get_areas():
    return get_areas()


@app.post("/api/set/area", tags=["area"])
async def fastapi_set_area(request: SetAreaRequest = Body(...)):
    resp = set_area(
        location=request.location,
        area_name=request.area_name,
        polygon_zone=request.polygon_zone,
    )

    if resp == SynapsisResponse.SUCCESS:
        return {"status": "success", "message": "Area set/updated successfully"}
    elif resp == SynapsisResponse.BAD_REQUEST:
        return {"status": "error", "message": "Area already exists"}
    else:
        return {"status": "error", "message": "Area set/update failed"}


@app.post("/api/get/area", tags=["area"])
async def fastapi_get_area(request: GetAreaRequest = Body(...)):
    resp = get_area(
        location=request.location,
        area_name=request.area_name,
    )
    resp["_id"] = str(resp["_id"])  # Cannot parse ObjectId to JSON directly

    if resp == SynapsisResponse.SERVER_ERROR:
        return {"status": "error", "message": "Get area failed"}
    elif resp == SynapsisResponse.NOT_FOUND:
        return {"status": "error", "message": "Area not found"}
    else:
        return {
            "status": "success",
            "message": "Area retrieved successfully",
            "data": resp,
        }


@app.post("/api/update/area", tags=["area"])
async def fastapi_update_area(request: UpdateAreaRequest = Body(...)):
    resp = update_area(
        location=request.location,
        area_name=request.area_name,
        polygon_zone=request.polygon_zone,
    )

    if resp == SynapsisResponse.SUCCESS:
        return {"status": "success", "message": "Area set/updated successfully"}
    elif resp == SynapsisResponse.NOT_FOUND:
        return {"status": "error", "message": "Area not found"}
    else:
        return {"status": "error", "message": "Area set/update failed"}


@app.post("/api/delete/area", tags=["area"])
async def fastapi_delete_area(request: DeleteAreaRequest = Body(...)):
    resp = delete_area(location=request.location, area_name=request.area_name)

    if resp == SynapsisResponse.SUCCESS:
        return {"status": "success", "message": "Area deleted successfully"}
    elif resp == SynapsisResponse.NOT_FOUND:
        return {"status": "error", "message": "Area not found"}
    else:
        return {"status": "error", "message": "Area deletion failed"}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
