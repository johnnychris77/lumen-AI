from importlib import import_module

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="LumenAI API")


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1|172\.27\.\d+\.\d+|10\.255\.255\.254):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "service": "LumenAI API"}


def include_router_from_candidates(candidate_modules, label):
    for module_path in candidate_modules:
        try:
            module = import_module(module_path)
            router = getattr(module, "router", None)

            if router is not None:
                app.include_router(router)
                print(f"Loaded router: {label} from {module_path}")
                return

        except Exception as error:
            last_error = error

    print(f"Router not loaded: {label}. Last error: {last_error}")


include_router_from_candidates(
    [
        "backend.app.routes.auth",
        "backend.app.routers.auth",
    ],
    "auth",
)

include_router_from_candidates(
    [
        "backend.app.routes.users",
        "backend.app.routers.users",
    ],
    "users",
)

include_router_from_candidates(
    [
        "backend.app.routes.reviews",
        "backend.app.routers.reviews",
    ],
    "reviews",
)

include_router_from_candidates(
    [
        "backend.app.routes.capa",
    ],
    "capa",
)

include_router_from_candidates(
    [
        "backend.app.routes.inspections",
    ],
    "inspections",
)


include_router_from_candidates(
    [
        "backend.app.routes.inspection_review",
    ],
    "inspection_review",
)


include_router_from_candidates(
    [
        "backend.app.routes.evidence",
    ],
    "evidence",
)
