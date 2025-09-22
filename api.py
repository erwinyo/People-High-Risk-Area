# Built-in imports

# Third-party imports
import uvicorn
from fastapi import FastAPI


# Local imports

app = FastAPI()


@app.get("/api/stats")
async def get_stats():
    return {"message": "Stats endpoint"}


@app.get("/api/stats/live")
async def get_stats_live():
    return {"message": "Live stats endpoint"}


@app.get("/api/config/area")
async def get_config_area():
    return {"message": "Config area endpoint"}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
