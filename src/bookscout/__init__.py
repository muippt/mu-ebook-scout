"""mu-ebook-scout: public-domain ebook meta-search across open sources."""

try:  # Python 3.8+ standard mechanism
    from importlib.metadata import PackageNotFoundError, version
except ImportError:  # pragma: no cover
    version = None

try:
    __version__ = version("mu-ebook-scout")
except Exception:  # PackageNotFoundError or version is None
    __version__ = "1.4.0"

__all__ = ["__version__"]
