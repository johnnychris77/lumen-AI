from fastapi import FastAPI
from backend.app.db.session import engine
from backend.app.db.base import Base
from backend.app.models import user, review  # ensure models are registered
from backend.app.routers import auth as auth_router
from backend.app.routers import users as users_router
from backend.app.routers import reviews as reviews_router
from backend.app.routes import capa
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI(title="LumenAI API")
app = FastAPI(title="LumenAI API")
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|172\.27\.41\.109|10\.255\.255\.254):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok": True}

@app.on_event("startup")
def on_startup():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print("DB init warning:", e)

app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(reviews_router.router)
<<<<<<< Updated upstream

from backend.app.routers.uploads import router as uploads_router
app.include_router(uploads_router, prefix='/uploads', tags=['uploads'])

=======
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(reviews_router.router)
app.include_router(capa.router)
>>>>>>> Stashed changes
