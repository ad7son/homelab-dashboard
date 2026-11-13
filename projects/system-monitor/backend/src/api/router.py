"""每次建立新的父 router，讓正式與相容前綴各自掛載。"""
from fastapi import APIRouter
from .routes import overview, history, health


def build_router() -> APIRouter:
    router = APIRouter()
    router.include_router(overview.router)
    router.include_router(history.router)
    router.include_router(health.router)
    return router
