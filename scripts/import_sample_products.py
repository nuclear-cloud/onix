#!/usr/bin/env python3
"""
Import sample products from JSON into database
"""
import json
import asyncio
from uuid import UUID
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import (
    CatalogProduct,
    Publisher,
    CatalogTitle,
    CatalogLanguage,
    CatalogSubject,
    CatalogExtent,
    CatalogMeasure,
    Contributor,
    CatalogProductContributor,
    CatalogTextContent,
    CatalogPublishingDate,
)


async def import_products():
    """Import sample products from JSON file"""
    
    # Read JSON file
    json_path = Path(__file__).parent.parent / "examples" / "sample_products.json"
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # Setup database
    db_url = settings.DATABASE_URL
    engine = create_async_engine(db_url, echo=False)
    
    async_session = sessionmaker(
        engine, 
        class_=AsyncSession, 
        expire_on_commit=False
    )
    
    async with async_session() as session:
        for product_data in data["products"]:
            print(f"Importing: {product_data['title']}")
            
            # Create publisher if needed
            pub_data = product_data.get("publisher")
            publisher = None
            if pub_data:
                publisher = await session.merge(
                    Publisher(
                        id=UUID(pub_data["id"]),
                        name=pub_data["name"],
                        gln=pub_data.get("gln")
                    )
                )
            
            # Create product
            product = CatalogProduct(
                id=UUID(product_data["id"]),
                record_reference=product_data["record_reference"],
                isbn_13=product_data.get("isbn_13"),
                ean=product_data.get("ean"),
                sku=product_data.get("sku"),
                product_form=product_data.get("product_form"),
                product_form_detail=product_data.get("product_form_detail"),
                publishing_status=product_data.get("publishing_status"),
                is_ukrainian=product_data.get("is_ukrainian", True),
                publisher_id=publisher.id if publisher else None,
                created_at=datetime.fromisoformat(product_data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(product_data["updated_at"].replace("Z", "+00:00")),
            )
            session.add(product)
            
            # Add titles
            for title_data in product_data.get("titles", []):
                title = CatalogTitle(
                    product_id=product.id,
                    type=title_data.get("type"),
                    title_text=title_data["title_text"],
                    subtitle=title_data.get("subtitle")
                )
                session.add(title)
            
            # Add languages
            for lang_data in product_data.get("languages", []):
                language = CatalogLanguage(
                    product_id=product.id,
                    role=lang_data.get("role"),
                    code=lang_data["code"]
                )
                session.add(language)
            
            # Add subjects (THEMA)
            for subject_data in product_data.get("subjects", []):
                subject = CatalogSubject(
                    product_id=product.id,
                    scheme_identifier=subject_data["scheme_identifier"],
                    subject_code=subject_data.get("subject_code"),
                    subject_heading_text=subject_data.get("subject_heading_text")
                )
                session.add(subject)
            
            # Add extents (pages, etc)
            for extent_data in product_data.get("extents", []):
                extent = CatalogExtent(
                    product_id=product.id,
                    type=extent_data.get("type"),
                    value=float(extent_data["value"]),
                    unit=extent_data.get("unit")
                )
                session.add(extent)
            
            # Add measures (height, width, weight)
            for measure_data in product_data.get("measures", []):
                measure = CatalogMeasure(
                    product_id=product.id,
                    type=measure_data.get("type"),
                    measurement=float(measure_data["measurement"]),
                    unit_code=measure_data.get("unit_code")
                )
                session.add(measure)
            
            # Add contributors
            contributors_by_id = {}
            for contrib_data in product_data.get("contributors", []):
                contrib_id = UUID(contrib_data["id"])
                contributor = Contributor(
                    id=contrib_id,
                    name=contrib_data["name"],
                    person_name_inverted=contrib_data.get("person_name_inverted")
                )
                session.add(contributor)
                contributors_by_id[contrib_id] = contributor
            
            # Link contributors to product
            for contrib_data in product_data.get("contributors", []):
                link = CatalogProductContributor(
                    product_id=product.id,
                    contributor_id=UUID(contrib_data["id"]),
                    role=contrib_data["role"],
                    sequence_number=contrib_data.get("sequence_number", 1)
                )
                session.add(link)
            
            # Add text content (blurbs, descriptions)
            for text_data in product_data.get("text_contents", []):
                text_content = CatalogTextContent(
                    product_id=product.id,
                    type=text_data.get("type"),
                    text=text_data["text"],
                    author=text_data.get("author")
                )
                session.add(text_content)
            
            # Add publishing date
            pub_date_data = product_data.get("publishing_date")
            if pub_date_data:
                pub_date = CatalogPublishingDate(
                    product_id=product.id,
                    role=pub_date_data.get("role"),
                    date_value=pub_date_data["date_value"],
                    date_format=pub_date_data.get("date_format")
                )
                session.add(pub_date)
        
        # Commit all changes
        await session.commit()
        print(f"\n✅ Successfully imported {len(data['products'])} products!")


if __name__ == "__main__":
    asyncio.run(import_products())
