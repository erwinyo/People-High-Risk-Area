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
    get_epoch_ms_iso_utc,
    get_areas,
    update_area,
    set_area,
    get_area,
)


class SetAreaRequest(BaseModel):
    location: str
    area_name: str
    polygon_zone: list[list[int]]


class GetAreaRequest(BaseModel):
    location: str
    area_name: str


app = FastAPI()


@app.get("/api/stats", tags=["status"])
async def fastapi_get_stats():
    return {"message": "Stats endpoint"}


@app.get("/api/stats/live", tags=["status"])
async def fastapi_get_stats_live():
    return {"message": "Live stats endpoint"}


@app.get("/api/area", tags=["area"])
async def fastapi_get_areas():
    return get_areas()


@app.post("/api/set/area", tags=["area"])
async def fastapi_set_area(request: SetAreaRequest = Body(...)):
    resp = set_area(
        {
            "location": request.location,
            "area_name": request.area_name,
            "polygon_zone": request.polygon_zone,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    if resp == SynapsisResponse.SUCCESS:
        return {"status": "success", "message": "Area set/updated successfully"}
    else:
        return {"status": "error", "message": resp.value}


@app.post("/api/get/area", tags=["area"])
async def fastapi_get_area(request: GetAreaRequest = Body(...)):
    resp = get_area(
        location=request.location,
        area_name=request.area_name,
    )

    if resp == SynapsisResponse.SERVER_ERROR:
        return {"status": "error", "message": "Get area failed"}
    else:
        return {
            "status": "success",
            "message": "Area retrieved successfully",
            "data": resp,
        }


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
