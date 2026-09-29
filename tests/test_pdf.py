from app.pdf import html_to_pdf


def test_html_to_pdf_returns_pdf_bytes():
    pdf_bytes = html_to_pdf("<h1>Test Contract</h1><p>Some [PLACEHOLDER] text.</p>")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")
    assert len(pdf_bytes) > 100
