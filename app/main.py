import datetime
import numpy as np
import os
import pandas as pd
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from routers import api, web

app = FastAPI()

app.include_router(web.router)
app.include_router(api.router)

app.mount("/assets", StaticFiles(directory="assets"), name="assets")


# @app.get("/")
# async def root():
#     return {"message": "welcome"}
