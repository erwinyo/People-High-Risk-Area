# Built-in imports

# Third-party imports
import uvicorn
from pydantic import BaseModel
from pymongo import MongoClient
from fastapi import FastAPI, Body


# Local imports


app = FastAPI()


@app.get("/api/stats")
async def get_stats():
    return {"message": "Stats endpoint"}


@app.get("/api/stats/live")
async def get_stats_live():
    return {"message": "Live stats endpoint"}


@app.post("/api/area")
async def get_area(r):
    return {"message": "Area endpoint"}

class AreaConfigRequest(BaseModel):
    area_id: str
    config_value: int


@app.post("/api/config/area")
async def setconfig_area(request: AreaConfigRequest = Body(...)):
    # Access parameters with request.area_id and request.config_value
    return {
        "message": "Config area endpoint",
        "area_id": request.area_id,
        "config_value": request.config_value,
    }


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
