# tests/test_blog_api.py
"""
Complete tests for Blog API.

Coverage:
  - Health check
  - Create post (success, validation, duplicate)
  - List posts (pagination, filtering)
  - Get single post (found, not found)
  - Update post (partial update, not found)
  - Delete post (success, not found)
  - Middleware headers
  - Schema validation

Run:
  pytest tests/ -v
  pytest tests/ -v --cov=app --cov-report=term-missing
"""

import pytest
from fastapi.testclient import TestClient


# ══════════════════════════════════════════════════════
# SECTION 1: HEALTH & ROOT
# ══════════════════════════════════════════════════════

class TestHealthAndRoot:

    def test_root_returns_200(self, client):
        """Root endpoint must return 200"""
        response = client.get("/")
        assert response.status_code == 200

    def test_root_returns_message(self, client):
        """Root must return welcome message"""
        response = client.get("/")
        data = response.json()
        assert "message" in data
        assert "Blog API" in data["message"]

    def test_health_returns_200(self, client):
        """Health endpoint must return 200"""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_returns_healthy_status(self, client):
        """Health must show status=healthy"""
        response = client.get("/health")
        data = response.json()
        assert data["status"] == "healthy"

    def test_health_shows_database_status(self, client):
        """Health must include database field"""
        response = client.get("/health")
        data = response.json()
        assert "database" in data

    def test_health_shows_service_name(self, client):
        """Health must include service name"""
        response = client.get("/health")
        data = response.json()
        assert data["service"] == "Blog API"

    def test_docs_accessible(self, client):
        """Swagger docs must be accessible"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_openapi_accessible(self, client):
        """OpenAPI JSON schema must be accessible"""
        response = client.get("/openapi.json")
        assert response.status_code == 200


# ══════════════════════════════════════════════════════
# SECTION 2: CREATE POST
# ══════════════════════════════════════════════════════

class TestCreatePost:

    def test_create_post_returns_201(self, client):
        """Creating a post must return 201 Created"""
        response = client.post("/posts", json={
            "title": "My First Post",
            "content": "This is the content of my first post.",
            "author": "Mahesh"
        })
        assert response.status_code == 201

    def test_create_post_returns_correct_data(self, client):
        """Created post must contain the data we sent"""
        payload = {
            "title": "FastAPI Tutorial",
            "content": "Learning FastAPI with PostgreSQL and Docker.",
            "author": "Mahesh"
        }
        response = client.post("/posts", json=payload)
        data = response.json()

        assert data["title"] == payload["title"]
        assert data["content"] == payload["content"]
        assert data["author"] == payload["author"]

    def test_create_post_assigns_id(self, client):
        """Created post must have an auto-assigned integer ID"""
        response = client.post("/posts", json={
            "title": "Post With ID",
            "content": "This post should get an auto ID.",
            "author": "Test"
        })
        data = response.json()
        assert "id" in data
        assert isinstance(data["id"], int)
        assert data["id"] > 0

    def test_create_post_default_published_true(self, client):
        """New posts must be published=True by default"""
        response = client.post("/posts", json={
            "title": "Published By Default",
            "content": "This should be published automatically.",
            "author": "Author"
        })
        data = response.json()
        assert data["published"] is True

    def test_create_post_returns_created_at(self, client):
        """Created post must have created_at timestamp"""
        response = client.post("/posts", json={
            "title": "Post With Timestamp",
            "content": "This post should have a timestamp.",
            "author": "Author"
        })
        data = response.json()
        assert "created_at" in data
        assert data["created_at"] is not None

    def test_create_duplicate_title_returns_409(self, client):
        """Creating two posts with same title must return 409 Conflict"""
        payload = {
            "title": "Unique Title",
            "content": "Content for the first post here.",
            "author": "Author"
        }
        # Create first post
        client.post("/posts", json=payload)

        # Try to create same title again
        response = client.post("/posts", json=payload)
        assert response.status_code == 409

    def test_create_post_title_too_short_returns_422(self, client):
        """Title less than 3 chars must return 422"""
        response = client.post("/posts", json={
            "title": "AB",       # too short — min_length=3
            "content": "Content that is long enough.",
            "author": "Author"
        })
        assert response.status_code == 422

    def test_create_post_content_too_short_returns_422(self, client):
        """Content less than 10 chars must return 422"""
        response = client.post("/posts", json={
            "title": "Valid Title",
            "content": "Short",   # too short — min_length=10
            "author": "Author"
        })
        assert response.status_code == 422

    def test_create_post_missing_title_returns_422(self, client):
        """Missing title must return 422"""
        response = client.post("/posts", json={
            "content": "Content without a title.",
            "author": "Author"
        })
        assert response.status_code == 422

    def test_create_post_missing_author_returns_422(self, client):
        """Missing author must return 422"""
        response = client.post("/posts", json={
            "title": "Post Without Author",
            "content": "Content without an author."
        })
        assert response.status_code == 422

    def test_create_post_empty_body_returns_422(self, client):
        """Empty request body must return 422"""
        response = client.post("/posts", json={})
        assert response.status_code == 422

    def test_create_post_author_too_short_returns_422(self, client):
        """Author less than 2 chars must return 422"""
        response = client.post("/posts", json={
            "title": "Valid Title",
            "content": "Valid content here.",
            "author": "A"         # too short — min_length=2
        })
        assert response.status_code == 422


# ══════════════════════════════════════════════════════
# SECTION 3: LIST POSTS
# ══════════════════════════════════════════════════════

class TestListPosts:

    def test_list_posts_returns_200(self, client):
        """List endpoint must return 200"""
        response = client.get("/posts")
        assert response.status_code == 200

    def test_list_posts_empty_returns_zero_total(self, client):
        """Empty database returns total=0"""
        response = client.get("/posts")
        data = response.json()
        assert data["total"] == 0
        assert data["posts"] == []

    def test_list_posts_returns_created_posts(self, client, multiple_posts):
        """List must return posts we created"""
        response = client.get("/posts")
        data = response.json()
        assert data["total"] == 5
        assert len(data["posts"]) == 5

    def test_list_posts_has_total_and_posts_fields(self, client):
        """Response must have total and posts fields"""
        response = client.get("/posts")
        data = response.json()
        assert "total" in data
        assert "posts" in data

    def test_list_posts_pagination_limit(self, client, multiple_posts):
        """limit param restricts number of results"""
        response = client.get("/posts?limit=2")
        data = response.json()
        assert len(data["posts"]) == 2
        assert data["total"] == 5  # total still shows all

    def test_list_posts_pagination_page(self, client, multiple_posts):
        """page param offsets results"""
        # Get page 1
        page1 = client.get("/posts?page=1&limit=2").json()
        # Get page 2
        page2 = client.get("/posts?page=2&limit=2").json()

        # Pages must have different posts
        page1_ids = {p["id"] for p in page1["posts"]}
        page2_ids = {p["id"] for p in page2["posts"]}
        assert page1_ids.isdisjoint(page2_ids)  # no overlap

    def test_list_posts_filter_by_author(self, client, multiple_posts):
        """author filter returns only that author's posts"""
        response = client.get("/posts?author=Author1")
        data = response.json()
        assert data["total"] == 1
        assert data["posts"][0]["author"] == "Author1"

    def test_list_posts_filter_nonexistent_author(self, client, multiple_posts):
        """Filter with unknown author returns empty"""
        response = client.get("/posts?author=UnknownAuthor")
        data = response.json()
        assert data["total"] == 0

    def test_list_posts_ordered_newest_first(self, client, multiple_posts):
        """Posts returned newest first"""
        response = client.get("/posts")
        data = response.json()
        # Last created post should be first in response
        ids = [p["id"] for p in data["posts"]]
        assert ids == sorted(ids, reverse=True)


# ══════════════════════════════════════════════════════
# SECTION 4: GET SINGLE POST
# ══════════════════════════════════════════════════════

class TestGetPost:

    def test_get_existing_post_returns_200(self, client, sample_post):
        """Getting existing post returns 200"""
        post_id = sample_post["id"]
        response = client.get(f"/posts/{post_id}")
        assert response.status_code == 200

    def test_get_post_returns_correct_data(self, client, sample_post):
        """Getting post returns correct title, content, author"""
        post_id = sample_post["id"]
        response = client.get(f"/posts/{post_id}")
        data = response.json()

        assert data["id"] == post_id
        assert data["title"] == sample_post["title"]
        assert data["author"] == sample_post["author"]

    def test_get_nonexistent_post_returns_404(self, client):
        """Getting post with wrong ID returns 404"""
        response = client.get("/posts/99999")
        assert response.status_code == 404

    def test_get_nonexistent_post_error_message(self, client):
        """404 error must include helpful message"""
        response = client.get("/posts/99999")
        data = response.json()
        assert "detail" in data
        assert "99999" in data["detail"]  # includes the ID in error


# ══════════════════════════════════════════════════════
# SECTION 5: UPDATE POST
# ══════════════════════════════════════════════════════

class TestUpdatePost:

    def test_update_title_returns_200(self, client, sample_post):
        """Updating title returns 200"""
        post_id = sample_post["id"]
        response = client.patch(f"/posts/{post_id}", json={"title": "Updated Title"})
        assert response.status_code == 200

    def test_update_title_changes_title(self, client, sample_post):
        """Updated title is reflected in response"""
        post_id = sample_post["id"]
        response = client.patch(f"/posts/{post_id}", json={"title": "New Title Here"})
        data = response.json()
        assert data["title"] == "New Title Here"

    def test_update_title_preserves_other_fields(self, client, sample_post):
        """Updating title does NOT change author or content"""
        post_id = sample_post["id"]
        original_author = sample_post["author"]
        original_content = sample_post["content"]

        response = client.patch(f"/posts/{post_id}", json={"title": "New Title"})
        data = response.json()

        # Other fields unchanged
        assert data["author"] == original_author
        assert data["content"] == original_content

    def test_update_published_status(self, client, sample_post):
        """Can unpublish a post"""
        post_id = sample_post["id"]
        response = client.patch(f"/posts/{post_id}", json={"published": False})
        data = response.json()
        assert data["published"] is False

    def test_update_multiple_fields(self, client, sample_post):
        """Can update multiple fields at once"""
        post_id = sample_post["id"]
        response = client.patch(f"/posts/{post_id}", json={
            "title": "Multi Update Title",
            "published": False
        })
        data = response.json()
        assert data["title"] == "Multi Update Title"
        assert data["published"] is False

    def test_update_nonexistent_post_returns_404(self, client):
        """Updating non-existent post returns 404"""
        response = client.patch("/posts/99999", json={"title": "New Title"})
        assert response.status_code == 404

    def test_update_title_too_short_returns_422(self, client, sample_post):
        """Updating with too-short title returns 422"""
        post_id = sample_post["id"]
        response = client.patch(f"/posts/{post_id}", json={"title": "AB"})
        assert response.status_code == 422

    def test_update_empty_body_returns_200(self, client, sample_post):
        """PATCH with empty body is valid — no fields updated"""
        post_id = sample_post["id"]
        response = client.patch(f"/posts/{post_id}", json={})
        # Empty patch is valid — nothing changes
        assert response.status_code == 200


# ══════════════════════════════════════════════════════
# SECTION 6: DELETE POST
# ══════════════════════════════════════════════════════

class TestDeletePost:

    def test_delete_post_returns_204(self, client, sample_post):
        """Deleting a post returns 204 No Content"""
        post_id = sample_post["id"]
        response = client.delete(f"/posts/{post_id}")
        assert response.status_code == 204

    def test_delete_post_returns_no_body(self, client, sample_post):
        """204 response has no body"""
        post_id = sample_post["id"]
        response = client.delete(f"/posts/{post_id}")
        assert response.content == b""  # empty body

    def test_deleted_post_not_retrievable(self, client, sample_post):
        """After deletion, post returns 404"""
        post_id = sample_post["id"]

        # Delete the post
        client.delete(f"/posts/{post_id}")

        # Try to get it — should be 404 now
        response = client.get(f"/posts/{post_id}")
        assert response.status_code == 404

    def test_deleted_post_not_in_list(self, client, sample_post):
        """After deletion, post does not appear in list"""
        post_id = sample_post["id"]

        # Delete the post
        client.delete(f"/posts/{post_id}")

        # Check list
        response = client.get("/posts")
        data = response.json()
        post_ids = [p["id"] for p in data["posts"]]
        assert post_id not in post_ids

    def test_delete_nonexistent_post_returns_404(self, client):
        """Deleting non-existent post returns 404"""
        response = client.delete("/posts/99999")
        assert response.status_code == 404

    def test_delete_post_reduces_count(self, client, multiple_posts):
        """After deletion, total count decreases"""
        # Initially 5 posts
        before = client.get("/posts").json()["total"]
        assert before == 5

        # Delete one
        post_id = multiple_posts[0]["id"]
        client.delete(f"/posts/{post_id}")

        # Now 4 posts
        after = client.get("/posts").json()["total"]
        assert after == 4


# ══════════════════════════════════════════════════════
# SECTION 7: MIDDLEWARE TESTS
# ══════════════════════════════════════════════════════

class TestMiddleware:

    def test_every_response_has_request_id_header(self, client):
        """Middleware must add X-Request-ID to every response"""
        response = client.get("/health")
        assert "x-request-id" in response.headers

    def test_every_response_has_duration_header(self, client):
        """Middleware must add X-Duration-Ms to every response"""
        response = client.get("/health")
        assert "x-duration-ms" in response.headers

    def test_request_id_is_unique_per_request(self, client):
        """Each request gets a unique request ID"""
        r1 = client.get("/health")
        r2 = client.get("/health")
        assert r1.headers["x-request-id"] != r2.headers["x-request-id"]

    def test_duration_is_numeric(self, client):
        """X-Duration-Ms header must be a valid number"""
        response = client.get("/health")
        duration = response.headers["x-duration-ms"]
        assert float(duration) >= 0  # valid number, 0 or more


# ══════════════════════════════════════════════════════
# SECTION 8: FULL WORKFLOW TEST
# ══════════════════════════════════════════════════════

class TestFullWorkflow:
    """
    End-to-end test: create → read → update → delete
    Tests the complete blog post lifecycle.
    """

    def test_complete_blog_post_lifecycle(self, client):
        """Full CRUD lifecycle in one test"""

        # STEP 1: Create post
        create_response = client.post("/posts", json={
            "title": "My Lifecycle Post",
            "content": "Testing the complete lifecycle of a blog post.",
            "author": "Mahesh"
        })
        assert create_response.status_code == 201
        post_id = create_response.json()["id"]

        # STEP 2: Read it back
        get_response = client.get(f"/posts/{post_id}")
        assert get_response.status_code == 200
        assert get_response.json()["title"] == "My Lifecycle Post"

        # STEP 3: Update it
        update_response = client.patch(f"/posts/{post_id}", json={
            "title": "Updated Lifecycle Post",
            "published": False
        })
        assert update_response.status_code == 200
        assert update_response.json()["title"] == "Updated Lifecycle Post"
        assert update_response.json()["published"] is False

        # STEP 4: Verify update persisted
        verify_response = client.get(f"/posts/{post_id}")
        assert verify_response.json()["title"] == "Updated Lifecycle Post"

        # STEP 5: Delete it
        delete_response = client.delete(f"/posts/{post_id}")
        assert delete_response.status_code == 204

        # STEP 6: Verify deletion
        final_response = client.get(f"/posts/{post_id}")
        assert final_response.status_code == 404

    def test_multiple_authors_isolated(self, client):
        """Posts from different authors don't interfere"""

        # Create posts from two authors
        client.post("/posts", json={
            "title": "Alice Post One",
            "content": "Content from Alice here.",
            "author": "Alice"
        })
        client.post("/posts", json={
            "title": "Bob Post One",
            "content": "Content from Bob here.",
            "author": "Bob"
        })

        # Filter by Alice
        alice_posts = client.get("/posts?author=Alice").json()
        assert alice_posts["total"] == 1
        assert alice_posts["posts"][0]["author"] == "Alice"

        # Filter by Bob
        bob_posts = client.get("/posts?author=Bob").json()
        assert bob_posts["total"] == 1
        assert bob_posts["posts"][0]["author"] == "Bob"