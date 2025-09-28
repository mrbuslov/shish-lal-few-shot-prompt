"""
Local HTML to PDF conversion utility
Uses weasyprint for converting HTML to PDF without external services
"""

from dataclasses import dataclass

try:
    from weasyprint import HTML, CSS

    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False
    print("Warning: weasyprint not available. Install with: pip install weasyprint")

try:
    import pdfkit

    PDFKIT_AVAILABLE = True
except ImportError:
    PDFKIT_AVAILABLE = False
    print("Warning: pdfkit not available. Install with: pip install pdfkit")


@dataclass
class ConversionResult:
    """Result of HTML to PDF conversion"""

    pdf_bytes: bytes
    filename: str
    content_type: str = "application/pdf"


class LocalConverter:
    """Local HTML to PDF converter using available libraries"""

    def __init__(self):
        self.preferred_engine = self._detect_best_engine()

    def _detect_best_engine(self) -> str:
        """Detect the best available conversion engine"""
        if WEASYPRINT_AVAILABLE:
            return "weasyprint"
        elif PDFKIT_AVAILABLE:
            return "pdfkit"
        else:
            raise ImportError(
                "No PDF conversion library available. "
                "Please install either weasyprint (pip install weasyprint) "
                "or pdfkit (pip install pdfkit)"
            )

    def html_to_pdf_weasyprint(
        self, html_content: str, filename: str
    ) -> ConversionResult:
        """Convert HTML to PDF using weasyprint"""
        if not WEASYPRINT_AVAILABLE:
            raise ImportError("weasyprint is not available")

        try:
            # Basic CSS for better PDF formatting
            base_css = CSS(
                string="""
                @page {
                    margin: 2cm;
                    size: A4;
                }
                body {
                    font-family: Arial, sans-serif;
                    font-size: 12pt;
                    line-height: 1.4;
                }
                h1, h2, h3 {
                    color: #333;
                    margin-top: 1em;
                    margin-bottom: 0.5em;
                }
                p {
                    margin-bottom: 0.5em;
                    text-align: justify;
                }
                table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 1em 0;
                }
                td, th {
                    border: 1px solid #ddd;
                    padding: 8px;
                    text-align: left;
                }
                th {
                    background-color: #f5f5f5;
                    font-weight: bold;
                }
            """
            )

            # Create HTML document and convert to PDF
            html_doc = HTML(string=html_content)
            pdf_bytes = html_doc.write_pdf(stylesheets=[base_css])

            # Ensure filename has .pdf extension
            if not filename.lower().endswith(".pdf"):
                filename = filename.rsplit(".", 1)[0] + ".pdf"

            return ConversionResult(
                pdf_bytes=pdf_bytes, filename=filename, content_type="application/pdf"
            )

        except Exception as e:
            raise Exception(f"Failed to convert HTML to PDF using weasyprint: {str(e)}")

    def html_to_pdf_pdfkit(self, html_content: str, filename: str) -> ConversionResult:
        """Convert HTML to PDF using pdfkit (wkhtmltopdf wrapper)"""
        if not PDFKIT_AVAILABLE:
            raise ImportError("pdfkit is not available")

        try:
            # PDF options for better formatting
            options = {
                "page-size": "A4",
                "margin-top": "2cm",
                "margin-right": "2cm",
                "margin-bottom": "2cm",
                "margin-left": "2cm",
                "encoding": "UTF-8",
                "no-outline": None,
                "enable-local-file-access": None,
            }

            # Convert HTML to PDF
            pdf_bytes = pdfkit.from_string(html_content, False, options=options)

            # Ensure filename has .pdf extension
            if not filename.lower().endswith(".pdf"):
                filename = filename.rsplit(".", 1)[0] + ".pdf"

            return ConversionResult(
                pdf_bytes=pdf_bytes, filename=filename, content_type="application/pdf"
            )

        except Exception as e:
            raise Exception(f"Failed to convert HTML to PDF using pdfkit: {str(e)}")

    def html_to_pdf(self, html_content: str, filename: str) -> ConversionResult:
        """Convert HTML to PDF using the best available engine"""
        if self.preferred_engine == "weasyprint":
            return self.html_to_pdf_weasyprint(html_content, filename)
        elif self.preferred_engine == "pdfkit":
            return self.html_to_pdf_pdfkit(html_content, filename)
        else:
            raise Exception("No PDF conversion engine available")

    def get_engine_info(self) -> dict:
        """Get information about available conversion engines"""
        return {
            "preferred_engine": self.preferred_engine,
            "weasyprint_available": WEASYPRINT_AVAILABLE,
            "pdfkit_available": PDFKIT_AVAILABLE,
        }


# Create singleton instance
pdf_converter = LocalConverter()


# Convenience functions
def html_to_pdf(html_content: str, filename: str = "document.pdf") -> ConversionResult:
    """Convert HTML to PDF - main convenience function"""
    return pdf_converter.html_to_pdf(html_content, filename)


def check_dependencies() -> dict:
    """Check which PDF conversion libraries are available"""
    return pdf_converter.get_engine_info()
