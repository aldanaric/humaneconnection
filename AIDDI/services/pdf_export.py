import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright
import markdown


def markdown_to_pdf(markdown_text: str) -> bytes:
    html_content = markdown.markdown(
        markdown_text,
        extensions=["fenced_code", "tables"]
    )

    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                line-height: 1.6;
            }}

            h1, h2, h3 {{
                color: #333;
            }}

            code {{
                background: #f4f4f4;
                padding: 2px 4px;
            }}

            table {{
                border-collapse: collapse;
                width: 100%;
            }}

            td, th {{
                border: 1px solid #ddd;
                padding: 8px;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """

    with tempfile.TemporaryDirectory() as tmp:
        html_file = Path(tmp) / "document.html"
        pdf_file = Path(tmp) / "document.pdf"

        html_file.write_text(full_html, encoding="utf-8")

        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            page.goto(f"file://{html_file}")

            page.pdf(
                path=str(pdf_file),
                format="Letter",
                print_background=True
            )

            browser.close()

        return pdf_file.read_bytes()
