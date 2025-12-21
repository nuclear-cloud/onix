"""
Concept: Core Unit Tests

This file contains unit tests for the core business logic of the application,
including ONIX XML generation, data validation, and embedding generation.
It uses mocking to avoid dependencies on the database or external AI models.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime
import pytest
from app.models.models import Product, Author, Publisher
from app.services.onix_service import OnixXmlGenerator
from app.services.validation_service import ValidationService
from app.services.embedding_service import EmbeddingService

# --- Test Data ---

SAMPLE_PRODUCT = Product(
    id="123e4567-e89b-12d3-a456-426614174000",
    isbn_13="9786171234567",
    title="Test Book Title",
    product_form="BC",
    language="ukr",
    onix_json={
        "prices": [{"price_amount": 300, "currency_code": "UAH"}],
        "text_content": [{"text_type": "03", "text": "Description"}],
        "supporting_resources": [{"resource_content_type": "01", "resource_mode": "03", "resource_link": "img.jpg"}]
    }
)

SAMPLE_AUTHOR = Author(
    id="123e4567-e89b-12d3-a456-426614174001",
    full_name="Test Author",
    biography="Bio"
)

SAMPLE_PUBLISHER = Publisher(
    id="123e4567-e89b-12d3-a456-426614174002",
    name="Test Publisher",
    gln="1234567890123"
)

# --- ONIX Service Tests ---

class TestOnixXmlGenerator:
    def test_generate_header(self):
        """Test that the ONIX header is generated correctly."""
        generator = OnixXmlGenerator(sender_name="Test Sender")
        # We accessed a private method for testing, but typically we test the public interface.
        # Let's test full generation instead.
        xml = generator.generate_product_xml(SAMPLE_PRODUCT, [SAMPLE_AUTHOR], SAMPLE_PUBLISHER)
        
        assert "Test Sender" in xml
        assert "ONIXMessage" in xml
        assert 'release="3.1"' in xml

    def test_generate_product_content(self):
        """Test that product details are correctly mapped to XML."""
        generator = OnixXmlGenerator()
        xml = generator.generate_product_xml(SAMPLE_PRODUCT, [SAMPLE_AUTHOR], SAMPLE_PUBLISHER)
        
        # Check ISBN
        assert "9786171234567" in xml
        # Check Title
        assert "Test Book Title" in xml
        # Check Author
        assert "Test Author" in xml
        # Check Publisher
        assert "Test Publisher" in xml
        # Check Price
        assert "300" in xml
        assert "UAH" in xml
        # Check Language
        assert "<LanguageCode>ukr</LanguageCode>" in xml

# --- Validation Service Tests ---

@pytest.mark.asyncio
class TestValidationService:
    async def test_validate_product_metadata_valid(self):
        """Test validation with valid data."""
        # Mock DB session
        mock_db = MagicMock()
        # Mock execute result to return True (found) for codelists
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("Description",) # Return a row
        mock_db.execute.return_value = mock_result
        
        service = ValidationService(mock_db)
        
        # Since execute is async, we need to mock it properly if it was awaited directly,
        # but SQLAlchemy AsyncSession.execute is awaitable. 
        # Making the mock return an awaitable is tricky with standard Mock.
        # Let's patch the validate_code method instead to avoid DB mocking complexity.
        
        with patch.object(ValidationService, 'validate_code', return_value=(True, None)):
            errors = await service.validate_product_metadata({
                "product_form": "BC",
                "language": "ukr",
                "authors": [{"role_code": "A01"}],
                "onix_json": {
                    "prices": [{"price_type": "01", "currency_code": "UAH"}],
                    "text_content": [{"text_type": "03"}]
                }
            })
            assert len(errors) == 0

    async def test_validate_product_metadata_invalid(self):
        """Test validation with invalid codes."""
        mock_db = MagicMock()
        service = ValidationService(mock_db)
        
        # Mock validate_code to fail
        with patch.object(ValidationService, 'validate_code', return_value=(False, "Invalid Code")):
            errors = await service.validate_product_metadata({
                "product_form": "INVALID",
            })
            assert len(errors) > 0
            assert "Invalid Code" in errors

# --- Embedding Service Tests ---

class TestEmbeddingService:
    @patch("app.services.embedding_service.SentenceTransformer")
    def test_generate_embedding(self, mock_model_cls):
        """Test embedding generation uses the model."""
        mock_model = mock_model_cls.return_value
        # Mock numpy array which has .tolist()
        mock_embedding = MagicMock()
        mock_embedding.tolist.return_value = [0.1, 0.2, 0.3]
        mock_model.encode.return_value = mock_embedding
        
        # Reset singleton if exists
        EmbeddingService._model = None
        
        embedding = EmbeddingService.generate_embedding("Test Text")
        
        assert len(embedding) == 3
        assert embedding == [0.1, 0.2, 0.3]
        
    def test_create_product_text(self):
        """Test text concatenation for embeddings."""
        text = EmbeddingService.create_product_text(
            title="Title",
            authors=["Author 1", "Author 2"],
            annotation="Description"
        )
        assert text == "Title by Author 1, Author 2 Description"
