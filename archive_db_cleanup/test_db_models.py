"""
Database Models Integration Tests.

Tests the full lifecycle of the ONIX Catalog & Market models:
Create -> Save -> Read -> Update Relations -> Offer Creation.
"""

import pytest
import pytest_asyncio
import uuid
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.database import Base, engine, AsyncSessionLocal
from app.models import (
    CatalogProduct,
    CatalogTitle,
    CatalogProductContributor,
    CatalogExtent,
    CatalogMeasure,
    CatalogSubject,
    CatalogTextContent,
    CatalogAudienceRange,
    CatalogRelatedProduct,
    Publisher,
    Supplier,
    Offer,
    ProductForm,
    ProductFormDetail,
    TitleType,
    ContributorRole,
    ExtentType,
    MeasureType,
    MeasureUnit,
    SubjectSchemeIdentifier,
    TextContentType,
    PublishingStatus,
    NotificationType,
    ProductAvailability
)

# Use this fixture to create a clean database session for each test
@pytest_asyncio.fixture
async def db_session():
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()

@pytest.mark.asyncio
async def test_full_product_lifecycle(db_session):
    """
    Test creating a complex ONIX product with all related tables.
    """
    
    # 1. Create Publisher
    publisher = Publisher(name=f"Test Publisher {uuid.uuid4()}", gln="1234567890123")
    db_session.add(publisher)
    await db_session.flush() # Get ID
    
    # 2. Create Product
    product = CatalogProduct(
        isbn_13="9780000000001",
        title="The Great Test Book",
        product_form=ProductForm.HARDCOVER,
        product_form_detail=ProductFormDetail.SEWN,
        publishing_status=PublishingStatus.ACTIVE,
        notification_type=NotificationType.NOTIFICATION_CONFIRMED,
        publisher_id=publisher.id,
        onix_full={"some": "json"} # Placeholder for full dump
    )
    db_session.add(product)
    await db_session.flush()
    
    # 3. Add Details (One-to-Many relations)
    
    # Titles
    t1 = CatalogTitle(product_id=product.id, type=TitleType.DISTINCTIVE_TITLE, text="The Great Test Book")
    t2 = CatalogTitle(product_id=product.id, type=TitleType.ORIGINAL_TITLE, text="La Grande Test Book", language="fre")
    db_session.add_all([t1, t2])
    
    # Contributors
    c1 = CatalogProductContributor(product_id=product.id, role=ContributorRole.AUTHOR, person_name="John Doe")
    c2 = CatalogProductContributor(product_id=product.id, role=ContributorRole.ILLUSTRATOR, person_name="Jane Art")
    db_session.add_all([c1, c2])
    
    # Subjects
    s1 = CatalogSubject(product_id=product.id, scheme_identifier=SubjectSchemeIdentifier.THEMA_SUBJECT, subject_code="FBA")
    db_session.add(s1)
    
    # Extents & Measures
    e1 = CatalogExtent(product_id=product.id, type=ExtentType.MAIN_PAGE_COUNT, value=300, unit="pages")
    m1 = CatalogMeasure(product_id=product.id, type=MeasureType.HEIGHT, measurement=200, unit_code=MeasureUnit.MILLIMETERS)
    db_session.add_all([e1, m1])
    
    # Text Content
    tc1 = CatalogTextContent(product_id=product.id, type=TextContentType.MAIN_DESCRIPTION, text="A very long description.")
    db_session.add(tc1)
    
    await db_session.commit()
    
    # 4. READ & VERIFY
    # Re-fetch product with all relations
    stmt = select(CatalogProduct).where(CatalogProduct.id == product.id).options(
        selectinload(CatalogProduct.titles),
        selectinload(CatalogProduct.contributors),
        selectinload(CatalogProduct.subjects),
        selectinload(CatalogProduct.extents),
        selectinload(CatalogProduct.measures),
        selectinload(CatalogProduct.publisher)
    )
    result = await db_session.execute(stmt)
    fetched_product = result.scalar_one()
    
    assert fetched_product.isbn_13 == "9780000000001"
    assert fetched_product.publisher.name.startswith("Test Publisher")
    assert len(fetched_product.titles) == 2
    assert len(fetched_product.contributors) == 2
    assert fetched_product.contributors[0].role in [ContributorRole.AUTHOR, ContributorRole.ILLUSTRATOR]
    assert len(fetched_product.measures) == 1
    assert fetched_product.measures[0].measurement == Decimal("200.00")
    
    print("\n✅ Catalog Product created and verified successfully!")
    
    
    # 5. MARKET: Create Offer
    
    # Get Yakaboo supplier (seeded in init_db, but we can't rely on it in test env unless we seed)
    # So create a test supplier
    supplier = Supplier(name=f"Test Supplier {uuid.uuid4()}", code=f"test_sup_{uuid.uuid4()}")
    db_session.add(supplier)
    await db_session.flush()
    
    offer = Offer(
        book_id=product.id,
        supplier_id=supplier.id,
        price=Decimal("450.00"),
        in_stock=True,
        availability=ProductAvailability.IN_STOCK,
        sku="YAK_12345"
    )
    db_session.add(offer)
    await db_session.commit()
    
    # Verify Offer
    stmt_offer = select(Offer).where(Offer.book_id == product.id)
    result_offer = await db_session.execute(stmt_offer)
    fetched_offer = result_offer.scalar_one()
    
    assert fetched_offer.price == Decimal("450.00")
    assert fetched_offer.sku == "YAK_12345"
    assert fetched_offer.supplier_id == supplier.id
    
    print("✅ Market Offer created and verified successfully!")

