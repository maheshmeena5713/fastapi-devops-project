# app/main.py
from fastapi import FastAPI, Depends, HTTPException, status, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import Optional
import structlog
import time
import uuid

from .database import engine, get_db, Base
from .models import Post
from .schemas import PostCreate, PostUpdate, PostResponse, PostListResponse

# ── Setup ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)  # create tables on startup
logger = structlog.get_logger()

# ── App ────────────────────────────────────────────────
app = FastAPI(
    title="Blog API",
    description="Simple blog with FastAPI + PostgreSQL + Docker + CI/CD",
    version="1.0.0"
)

# ── CORS ───────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # in production: specify exact origin
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)

# ── Middleware: Request Logging ────────────────────────
# This runs BEFORE and AFTER every request
# Teaches: @app.middleware("http"), call_next, request_id


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()

    logger.info(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path
    )

    response = await call_next(request)  # run the actual endpoint
    duration_ms = round((time.time() - start) * 1000, 2)

    logger.info(
        "request_completed",
        request_id=request_id,
        status_code=response.status_code,
        duration_ms=duration_ms
    )

    response.headers["X-Request-ID"] = request_id
    response.headers["X-Duration-Ms"] = str(duration_ms)
    return response


# ── Background Task ────────────────────────────────────
# Runs AFTER response is sent — client doesn't wait
def log_post_created(post_id: int, title: str, author: str):
    """
    This runs after response is sent.
    Used for analytics, notifications, audit logs.
    """
    logger.info(
        "post_created_event",
        post_id=post_id,
        title=title,
        author=author,
        event="NEW_POST"
    )


# ══════════════════════════════════════════════════════
# ENDPOINTS
# ══════════════════════════════════════════════════════

# ── Health Check ───────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Kubernetes uses this to check if app is alive.
    Also checks DB connection.
    """
    try:
        db.execute(__import__("sqlalchemy").text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"

    return {
        "status": "healthy",
        "database": db_status,
        "service": "Blog API",
        "version": "1.0.0"
    }


# ── Root ───────────────────────────────────────────────
@app.get("/", tags=["Root"])
def root():
    return {
        "message": "Blog API Running",
        "docs": "/docs",
        "health": "/health"
    }


# ── Create Post ────────────────────────────────────────
@app.post(
    "/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Posts"]
)
def create_post(
    data: PostCreate,
    background_tasks: BackgroundTasks,    # background task injection
    db: Session = Depends(get_db)         # DB injection via Depends
):
    """
    Create a new blog post.
    - Validates input with Pydantic
    - Saves to PostgreSQL
    - Logs creation in background (after response sent)
    """
    # Check duplicate title
    existing = db.query(Post).filter(Post.title == data.title).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Post with title '{data.title}' already exists"
        )

    # Create post
    post = Post(
        title=data.title,
        content=data.content,
        author=data.author
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    # Background task — runs AFTER response sent
    background_tasks.add_task(
        log_post_created,
        post_id=post.id,
        title=post.title,
        author=post.author
    )

    return post


# ── List Posts ─────────────────────────────────────────
@app.get(
    "/posts",
    response_model=PostListResponse,
    tags=["Posts"]
)
def list_posts(
    page: int = 1,
    limit: int = 10,
    author: Optional[str] = None,          # filter by author
    published: Optional[bool] = True,       # filter published only
    db: Session = Depends(get_db)
):
    """
    List posts with pagination and filtering.
    Shows: query params, filtering, pagination.
    """
    query = db.query(Post)

    # Apply filters
    if author:
        query = query.filter(Post.author == author)
    if published is not None:
        query = query.filter(Post.published == published)

    # Total count BEFORE pagination
    total = query.count()

    # Apply pagination
    offset = (page - 1) * limit
    posts = query.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()

    return PostListResponse(total=total, posts=posts)


# ── Get Single Post ────────────────────────────────────
@app.get(
    "/posts/{post_id}",
    response_model=PostResponse,
    tags=["Posts"]
)
def get_post(post_id: int, db: Session = Depends(get_db)):
    """Get one post by ID."""
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post {post_id} not found"
        )
    return post


# ── Update Post ────────────────────────────────────────
@app.patch(
    "/posts/{post_id}",
    response_model=PostResponse,
    tags=["Posts"]
)
def update_post(
    post_id: int,
    data: PostUpdate,
    db: Session = Depends(get_db)
):
    """
    Partial update — PATCH updates only provided fields.
    PUT would replace the entire resource.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Update only fields that were provided
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post


# ── Delete Post ────────────────────────────────────────
@app.delete(
    "/posts/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Posts"]
)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    """
    Delete a post. Returns 204 No Content — no body.
    """
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    db.delete(post)
    db.commit()
    # 204 returns no body — FastAPI handles this automatically