# tests/test_imports.py
import receptus

def test_has_version():
    assert hasattr(receptus, "__version__")

def test_public_api_imports():
    from receptus import Receptus, UserQuit
