from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parents[1] / "src" / "dm_assistant_core"


def test_domain_does_not_import_adapters_or_api() -> None:
    domain_source = "\n".join(
        path.read_text(encoding="utf-8") for path in (SOURCE_ROOT / "domain").glob("*.py")
    )

    assert "dm_assistant_core.adapters" not in domain_source
    assert "dm_assistant_core.api" not in domain_source


def test_persistence_is_confined_to_adapter_package() -> None:
    offenders: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        if "adapters" in path.parts:
            continue
        if "import psycopg" in path.read_text(encoding="utf-8"):
            offenders.append(str(path.relative_to(SOURCE_ROOT)))

    assert offenders == []


def test_canonical_table_writes_exist_only_in_migrations() -> None:
    canonical_write_tokens = (
        "INSERT INTO entities",
        "INSERT INTO claims",
        "INSERT INTO relationships",
        "UPDATE entities",
        "UPDATE claims",
        "UPDATE relationships",
    )
    offenders: list[str] = []
    for path in SOURCE_ROOT.rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        if any(token in source for token in canonical_write_tokens):
            offenders.append(str(path.relative_to(SOURCE_ROOT)))

    assert offenders == []


def test_production_importer_does_not_depend_on_test_harness_or_psycopg() -> None:
    importer_source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (SOURCE_ROOT / "importer").glob("*.py")
    )

    assert "tests.support" not in importer_source
    assert "import psycopg" not in importer_source
    assert "from psycopg" not in importer_source


def test_source_scanner_contains_no_filesystem_mutation_calls() -> None:
    scanner_source = (SOURCE_ROOT / "importer" / "scanner.py").read_text(encoding="utf-8")
    forbidden = (
        ".write_bytes(",
        ".write_text(",
        ".unlink(",
        ".rename(",
        ".replace(",
        ".mkdir(",
        ".touch(",
        "shutil.move",
        "shutil.rmtree",
    )

    assert not any(token in scanner_source for token in forbidden)
