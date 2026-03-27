"""
GoKwik Rate Capture Automation - FastAPI Application

Creates the FastAPI app, configures CORS, and includes all route modules.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import phase1, phase2, auto_process, email, drive, playwright, gokwik_auto

app = FastAPI(title="GoKwik Rate Capture Automation API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(phase1.router)
app.include_router(phase2.router)
app.include_router(auto_process.router)
app.include_router(email.router)
app.include_router(drive.router)
app.include_router(playwright.router)
app.include_router(gokwik_auto.router)
