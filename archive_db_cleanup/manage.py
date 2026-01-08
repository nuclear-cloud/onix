#!/usr/bin/env python3
"""
📚 ONIX Standardizer - CLI

Система стандартизації даних про книги у формат ONIX.

Usage:
    python manage.py standardize data/books.jsonl
    python manage.py detect-format data/books.jsonl
    python manage.py validate-onix output/books_onix.jsonl
"""

import sys
import os
from typing import Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import typer
from rich.console import Console

app = typer.Typer(
    name="onix-standardizer",
    help="📚 ONIX Standardizer - Система стандартизації даних про книги",
    add_completion=False,
)
console = Console()


@app.command(name="standardize")
def standardize_data(
    input_file: str = typer.Argument(..., help="Шлях до вхідного JSONL файлу"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Шлях до вихідного файлу (за замовчуванням: input_onix.jsonl)"),
    format: Optional[str] = typer.Option(None, "--format", "-f", help="Примусово вказати формат (yakaboo, vivat, generic)"),
    batch_size: int = typer.Option(1000, "--batch-size", "-b", help="Розмір батчу для обробки"),
    skip_errors: bool = typer.Option(True, "--skip-errors/--fail-on-error", help="Пропускати помилки чи зупинятися"),
):
    """
    📚 Стандартизує дані з JSONL файлу в формат ONIX.
    
    Приклади:
        python manage.py standardize data/books.jsonl
        python manage.py standardize data/books.jsonl -o output/books_onix.jsonl
        python manage.py standardize data/yakaboo.jsonl --format yakaboo
    """
    from app.services.pipeline import etl_service
    
    try:
        # Use new Unified ETL Service
        stats = etl_service.process_file(
            input_path=input_file,
            output_path=output_file,
            format_override=format
        )
        
        console.print(f"\n[green]✅ Обробку завершено успішно![/green]")
        return stats
    except Exception as e:
        console.print(f"[red]❌ Помилка: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command(name="detect-format")
def detect_format(
    input_file: str = typer.Argument(..., help="Шлях до JSONL файлу"),
    sample_size: int = typer.Option(100, "--sample", "-s", help="Кількість рядків для аналізу"),
):
    """
    🔍 Визначає формат даних у JSONL файлі.
    
    Приклад:
        python manage.py detect-format data/books.jsonl
    """
    import json
    from collections import Counter
    from app.processors.format_detector import FormatDetector
    
    formats = Counter()
    isbns_found = 0
    titles_found = 0
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                
                try:
                    data = json.loads(line.strip())
                    fmt = FormatDetector.detect_format(data)
                    formats[fmt] += 1
                    
                    if FormatDetector.extract_isbn(data):
                        isbns_found += 1
                    if FormatDetector.extract_title(data):
                        titles_found += 1
                except json.JSONDecodeError:
                    continue
        
        console.print(f"\n[bold]📊 Аналіз формату даних[/bold]")
        console.print(f"Проаналізовано рядків: {min(sample_size, i+1)}")
        console.print(f"\n[bold]Формати:[/bold]")
        for fmt, count in formats.most_common():
            percentage = (count / (i+1)) * 100
            console.print(f"  {fmt}: {count} ({percentage:.1f}%)")
        
        console.print(f"\n[bold]Якість даних:[/bold]")
        console.print(f"  ISBN знайдено: {isbns_found}/{i+1} ({isbns_found/(i+1)*100:.1f}%)")
        console.print(f"  Назви знайдено: {titles_found}/{i+1} ({titles_found/(i+1)*100:.1f}%)")
        
    except FileNotFoundError:
        console.print(f"[red]❌ Файл не знайдено: {input_file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Помилка: {str(e)}[/red]")
        raise typer.Exit(1)


@app.command(name="validate-onix")
def validate_onix(
    input_file: str = typer.Argument(..., help="Шлях до ONIX JSONL файлу"),
    sample_size: int = typer.Option(100, "--sample", "-s", help="Кількість рядків для перевірки"),
):
    """
    ✅ Валідує ONIX дані у файлі.
    
    Приклад:
        python manage.py validate-onix data/books_onix.jsonl
    """
    import json
    
    required_fields = ["product_identifier", "titles"]
    issues = []
    valid_count = 0
    
    try:
        with open(input_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= sample_size:
                    break
                
                try:
                    data = json.loads(line.strip())
                    
                    # Перевірка обов'язкових полів
                    missing = [field for field in required_fields if not data.get(field)]
                    if missing:
                        issues.append(f"Рядок {i+1}: відсутні поля {', '.join(missing)}")
                    else:
                        valid_count += 1
                    
                    # Перевірка ISBN
                    has_isbn = False
                    for pi in data.get("product_identifier", []):
                        if pi.get("type") in ("15", "02"):
                            has_isbn = True
                            break
                    
                    if not has_isbn:
                        issues.append(f"Рядок {i+1}: відсутній ISBN")
                    
                except json.JSONDecodeError as e:
                    issues.append(f"Рядок {i+1}: помилка JSON - {str(e)}")
            
            console.print(f"\n[bold]📊 Валідація ONIX даних[/bold]")
            console.print(f"Перевірено рядків: {min(sample_size, i+1)}")
            console.print(f"[green]✅ Валідних: {valid_count}[/green]")
            console.print(f"[red]❌ Проблем: {len(issues)}[/red]")
            
            if issues:
                console.print(f"\n[bold]Перші 10 проблем:[/bold]")
                for issue in issues[:10]:
                    console.print(f"  • {issue}")
            
    except FileNotFoundError:
        console.print(f"[red]❌ Файл не знайдено: {input_file}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Помилка: {str(e)}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
