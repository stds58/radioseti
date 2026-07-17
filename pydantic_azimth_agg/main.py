from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn
from typing import List, Optional
from schema1 import build_hierarchy, Avtocod
from data_example import data


app = FastAPI(
title="Hierarchy API",
    docs_url="/docs",
    redoc_url="/redoc"
)


@app.get("/hierarchy", response_model=List[Avtocod])
async def get_hierarchy():
    hierarchy = build_hierarchy(data)
    return JSONResponse(content=[obj.to_dict() for obj in hierarchy])


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
