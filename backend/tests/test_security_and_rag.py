"""Test suite for security, hashing, JWT token mechanics, and RAG citation validation."""
import numpy as np
from app.core.security import hash_password, verify_password, create_access_token, decode_token
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.ingestion import IngestionService


def test_password_hashing():
    pw = "SuperSecurePassword123!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False


def test_jwt_token_flow():
    user_id = "test-user-uuid-1234"
    token = create_access_token(user_id)
    decoded = decode_token(token)

    assert decoded["sub"] == user_id
    assert decoded["type"] == "access"


def test_ingestion_path_traversal_prevention():
    assert IngestionService.is_safe_path("src/index.js") is True
    assert IngestionService.is_safe_path("app/models/user.py") is True
    assert IngestionService.is_safe_path("../etc/passwd") is False
    assert IngestionService.is_safe_path("foo/../../bar") is False


def test_vector_cosine_similarity():
    v1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v2 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    v3 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    sim_identical = EmbeddingService.cosine_similarity(v1, v2)
    sim_orthogonal = EmbeddingService.cosine_similarity(v1, v3)

    assert np.isclose(sim_identical, 1.0)
    assert np.isclose(sim_orthogonal, 0.0)


def test_citation_validation():
    chunks = [
        {
            "file_path": "backend/app/main.py",
            "start_line": 1,
            "end_line": 40,
            "content": "app = FastAPI()",
        }
    ]
    response_with_valid_citation = "The app is initialized in [backend/app/main.py:L1-L40]."
    response_with_invalid_citation = "Non-existent feature in [backend/fake/service.py:L10-L20]."

    valid_cits = LLMService.validate_citations(response_with_valid_citation, chunks)
    assert len(valid_cits) == 1
    assert valid_cits[0]["file_path"] == "backend/app/main.py"

    invalid_cits = LLMService.validate_citations(response_with_invalid_citation, chunks)
    assert len(invalid_cits) == 0
