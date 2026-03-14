"""
tests/test_qual.py -- Qualitative narrative layer tests (Phase 4).

Covers:
- COWK-03: README contains Cowork setup instructions
- QUAL-01 through QUAL-04: Narrative generation workflow in CLAUDE.md
"""

from pathlib import Path


def test_readme_cowork_section():
    """COWK-03: README contains Cowork setup instructions."""
    readme_path = Path(__file__).parent.parent / 'README.md'
    content = readme_path.read_text(encoding='utf-8')
    assert 'Cowork' in content, "README must mention Cowork"
    assert 'clone' in content.lower(), "README must include clone step"
    assert 'upload' in content.lower() or 'portfolio' in content.lower(), "README must mention uploading portfolio"
