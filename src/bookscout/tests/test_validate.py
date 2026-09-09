"""Magic-number validation tests using small synthetic files."""
from bookscout.core.validate import sniff_format


class TestSniffFormat:
    def test_epub_zip_magic(self, tmp_path):
        f = tmp_path / "book.epub"
        f.write_bytes(b"PK\x03\x04" + b"\x00" * 64)
        assert sniff_format(f) == "EPUB"

    def test_empty_zip_magic_is_epub(self, tmp_path):
        f = tmp_path / "empty.epub"
        f.write_bytes(b"PK\x05\x06" + b"\x00" * 18)
        assert sniff_format(f) == "EPUB"

    def test_mobi_magic_at_offset_60(self, tmp_path):
        f = tmp_path / "book.mobi"
        f.write_bytes(b"\x00" * 60 + b"BOOKMOBI" + b"\xff" * 16)
        assert sniff_format(f) == "MOBI"

    def test_pdf_magic(self, tmp_path):
        f = tmp_path / "book.pdf"
        f.write_bytes(b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n" + b"\x00" * 32)
        assert sniff_format(f) == "PDF"

    def test_plain_text_is_unknown(self, tmp_path):
        f = tmp_path / "book.txt"
        f.write_bytes(b"just some plain text, not a book container")
        assert sniff_format(f) is None

    def test_empty_file_is_unknown(self, tmp_path):
        f = tmp_path / "empty.bin"
        f.write_bytes(b"")
        assert sniff_format(f) is None

    def test_truncated_mobi_header_is_unknown(self, tmp_path):
        # Fewer than 68 bytes: BOOKMOBI cannot legally appear.
        f = tmp_path / "short.mobi"
        f.write_bytes(b"\x00" * 30 + b"BOOKMOBI")
        assert sniff_format(f) is None

    def test_missing_file_is_unknown(self, tmp_path):
        assert sniff_format(tmp_path / "nope.epub") is None

    def test_string_path_accepted(self, tmp_path):
        f = tmp_path / "book.pdf"
        f.write_bytes(b"%PDF-1.4\n")
        assert sniff_format(str(f)) == "PDF"
