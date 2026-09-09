"""Built-in source registry + custom source loading.

Built-in sources are all public-domain / open-access and are searched by
the engine in order. Custom sources come from the user's config file and
are always LINK_ONLY pass-throughs.
"""
from __future__ import annotations

from bookscout.core.model import Source
from bookscout.sources.cbeta import CbetaSource
from bookscout.sources.custom import get_custom_sources
from bookscout.sources.ctext import CtextViewSource
from bookscout.sources.github_books import GithubBooksSource
from bookscout.sources.github_lists import GithubBookListsSource
from bookscout.sources.google_books import GoogleBooksSource
from bookscout.sources.gutenberg import GutenbergSource
from bookscout.sources.librivox import LibrivoxSource
from bookscout.sources.openlibrary import OpenLibrarySource
from bookscout.sources.standard_ebooks import StandardEbooksSource
from bookscout.sources.wikisource import WikisourceSource

__all__ = [
    "SOURCE_REGISTRY",
    "get_custom_sources",
    "GutenbergSource",
    "OpenLibrarySource",
    "WikisourceSource",
    "StandardEbooksSource",
    "CbetaSource",
    "CtextViewSource",
    "GithubBooksSource",
    "GithubBookListsSource",
    "GoogleBooksSource",
    "LibrivoxSource",
]

#: All built-in, legal (public-domain / open-license) sources.
SOURCE_REGISTRY: list[Source] = [
    GutenbergSource(),
    OpenLibrarySource(),
    WikisourceSource(),
    StandardEbooksSource(),
    CbetaSource(),
    CtextViewSource(),
    GithubBooksSource(),
    GithubBookListsSource(),
    GoogleBooksSource(),
    LibrivoxSource(),
]
