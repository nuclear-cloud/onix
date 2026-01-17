from app.core.engine.worker import UniversalWorker
import json

# Mock config
worker = UniversalWorker("app/core/adapters/vivat.json", "redis://localhost")

# Sample data (real from API)
data = {
    "id": "61969",
    "type": "product",
    "attributes": {
        "product.id": "61969",
        "product.url": "tuli-tuli",
        "product.code": "1577344",
        "product.label": "Тулі-Тулі"
    },
    "relationships": {
        "price": {
            "data": [
                {
                    "attributes": {
                        "price.value": "590.00"
                    }
                }
            ]
        },
        "attribute": {
            "data": [
                {
                    "attributes": {
                        "attribute.type": "ean_isbn",
                        "attribute.code": "9786178318222"
                    }
                }
            ]
        }
    }
}

# Test selectors from adapter
print(f"Title: {worker._extract_value(data, ['attributes', 'product.label'])}")
print(f"SKU: {worker._extract_value(data, ['attributes', 'product.code'])}")
print(f"Price: {worker._extract_value(data, ['relationships', 'price', 'data', 0, 'attributes', 'price.value'])}")

isbn_selector = {
      "path": ["relationships", "attribute", "data"],
      "filter": {
        "key": ["attributes", "attribute.type"],
        "value": "ean_isbn"
      },
      "extract": ["attributes", "attribute.code"]
    }
print(f"ISBN: {worker._extract_value(data, isbn_selector)}")
