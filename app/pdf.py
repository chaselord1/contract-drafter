"""Renders the edited contract HTML into a printable PDF with xhtml2pdf."""
from __future__ import annotations

import io

from xhtml2pdf import pisa

PRINT_CSS = """
@page {
    size: letter;
    margin: 1in;
    @frame footer_frame {
        -pdf-frame-content: footer_content;
        bottom: 0.4in;
        margin-left: 1in;
        margin-right: 1in;
        height: 0.4in;
    }
}
body {
    font-family: "Times New Roman", Times, serif;
    font-size: 11pt;
    line-height: 1.5;
    color: #111;
}
h1 {
    font-size: 16pt;
    text-align: center;
    margin-bottom: 0.3in;
}
h2 {
    font-size: 12pt;
    margin-top: 0.25in;
    margin-bottom: 0.1in;
}
p {
    margin: 0 0 0.12in 0;
    text-align: justify;
}
ol, ul {
    margin: 0 0 0.12in 0.25in;
}
.placeholder {
    background-color: #fff3b0;
}
#footer_content {
    font-size: 8pt;
    text-align: center;
    color: #666;
}
"""


def html_to_pdf(body_html: str) -> bytes:
    """Wraps the draft's body HTML in a print stylesheet and renders a PDF.

    Returns raw PDF bytes starting with %PDF.
    """
    full_html = f"""<html>
<head><style>{PRINT_CSS}</style></head>
<body>
{body_html}
<div id="footer_content">Page <pdf:pagenumber /> of <pdf:pagecount /></div>
</body>
</html>"""

    buffer = io.BytesIO()
    result = pisa.CreatePDF(src=full_html, dest=buffer)
    if result.err:
        raise RuntimeError(f"PDF generation failed with {result.err} error(s)")
    return buffer.getvalue()
