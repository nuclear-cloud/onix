# Contributing to ONIX Aggregator

Thank you for considering contributing to the ONIX Aggregator project! 🎉

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone git@github.com:YOUR_USERNAME/onix.git
   cd onix
   ```

3. **Set up the development environment**:
   ```bash
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Generate Prisma client
   prisma generate
   
   # Copy environment template
   cp .env.example .env
   # Edit .env with your database credentials
   ```

4. **Set up the database**:
   ```bash
   # Create PostgreSQL database
   createdb onix_db
   
   # Initialize schema
   python scripts/init_final_db.py --force
   ```

## Development Workflow

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following our coding standards

3. **Write tests** for new functionality

4. **Run tests**:
   ```bash
   pytest -v
   ```

5. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: your descriptive commit message"
   ```

## Commit Message Convention

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Maintenance tasks

Examples:
```
feat: Add Prisma ORM integration
fix: Correct ISBN-13 validation logic
docs: Update Prisma usage examples
```

## Code Style

- **Python**: Follow PEP 8
- **Line length**: Max 100 characters
- **Imports**: Use absolute imports
- **Type hints**: Use type hints for function signatures
- **Docstrings**: Use Google-style docstrings

Example:
```python
async def get_book_by_isbn(isbn13: str) -> Optional[CatalogProduct]:
    """
    Retrieve a book by its ISBN-13.
    
    Args:
        isbn13: The 13-digit ISBN of the book
        
    Returns:
        The book if found, None otherwise
    """
    # Implementation here
```

## Project Structure

```
onix_project/
├── app/
│   ├── models/          # SQLAlchemy models
│   ├── schemas/         # Pydantic schemas
│   ├── services/        # Business logic
│   ├── adapters/        # Data source adapters
│   └── repositories/    # Data access layer
├── scripts/             # Utility scripts
├── tests/               # Test files
├── docs/                # Documentation
├── examples/            # Usage examples
└── prisma/              # Prisma schema
```

## Testing

- Write unit tests for new functionality
- Ensure all tests pass before submitting PR
- Aim for good test coverage

```bash
# Run all tests
pytest -v

# Run specific test file
pytest tests/test_catalog_loader.py -v

# Run with coverage
pytest --cov=app tests/
```

## Documentation

- Update documentation for any user-facing changes
- Add docstrings to new functions/classes
- Update README.md if adding new features
- Create examples for new functionality

## Pull Request Process

1. **Update documentation** as needed
2. **Ensure all tests pass**
3. **Update CHANGELOG** (if exists)
4. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

5. **Create Pull Request** on GitHub:
   - Provide clear description of changes
   - Reference related issues
   - Add screenshots/examples if applicable

## Areas for Contribution

### High Priority
- 🔍 Additional retailer adapters (Book-ye, Knygarnya Ye, etc.)
- 📊 Price comparison analytics
- 🔄 Automated data quality checks
- 📱 REST API endpoints

### Medium Priority
- 🎨 Web UI for catalog browsing
- 📈 Performance optimizations
- 🧪 Additional test coverage
- 📚 More documentation and examples

### Good First Issues
- 🐛 Bug fixes
- 📝 Documentation improvements
- ✨ Code style improvements
- 🧹 Refactoring

## Questions?

- Check existing [documentation](./docs/)
- Look at [examples](./examples/)
- Open an issue for discussion

## Code of Conduct

Be respectful and inclusive. We're all here to build something useful together!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
