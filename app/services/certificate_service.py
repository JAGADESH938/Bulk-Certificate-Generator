import io
import uuid
from datetime import date
from pathlib import Path
from typing import Union

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas

from app.services.storage_service import storage_service


class CertificateService:
    """Service responsible for generating professional PDF certificates using ReportLab."""

    PAGE_WIDTH, PAGE_HEIGHT = landscape(letter)  # 792 x 612 points

    # Professional color palette
    NAVY_PRIMARY = colors.HexColor("#0F2942")
    GOLD_ACCENT = colors.HexColor("#C59B27")
    GOLD_LIGHT = colors.HexColor("#F3E5AB")
    SLATE_GRAY = colors.HexColor("#4A5568")
    LIGHT_BG = colors.HexColor("#FAFAFA")
    TEXT_DARK = colors.HexColor("#1A202C")

    def __init__(self) -> None:
        self.template_path = Path(__file__).parent.parent / "templates" / "certificate_template.pdf"

    def _draw_borders(self, c: canvas.Canvas) -> None:
        """Draw professional multi-tier certificate borders and corner ornaments."""
        w, h = self.PAGE_WIDTH, self.PAGE_HEIGHT

        # Outer background tint
        c.setFillColor(self.LIGHT_BG)
        c.rect(0, 0, w, h, fill=True, stroke=False)

        # Primary Navy Outer Border
        c.setStrokeColor(self.NAVY_PRIMARY)
        c.setLineWidth(4)
        c.rect(28, 28, w - 56, h - 56, fill=False, stroke=True)

        # Secondary Gold Inner Border
        c.setStrokeColor(self.GOLD_ACCENT)
        c.setLineWidth(1.5)
        c.rect(36, 36, w - 72, h - 72, fill=False, stroke=True)

        # Thin Inner Framing Line
        c.setStrokeColor(colors.HexColor("#CBD5E1"))
        c.setLineWidth(0.5)
        c.rect(42, 42, w - 84, h - 84, fill=False, stroke=True)

        # Corner Accents (Decorative corner diamonds)
        corner_offsets = [
            (36, 36),
            (w - 36, 36),
            (36, h - 36),
            (w - 36, h - 36),
        ]
        c.setFillColor(self.GOLD_ACCENT)
        for cx, cy in corner_offsets:
            p = c.beginPath()
            p.moveTo(cx, cy + 6)
            p.lineTo(cx + 6, cy)
            p.lineTo(cx, cy - 6)
            p.lineTo(cx - 6, cy)
            p.close()
            c.drawPath(p, fill=True, stroke=False)

    def _draw_header(self, c: canvas.Canvas) -> None:
        """Draw top banner and certificate title."""
        w, h = self.PAGE_WIDTH, self.PAGE_HEIGHT

        # Top tag
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.GOLD_ACCENT)
        c.drawCentredString(w / 2, h - 90, "★   OFFICIAL CERTIFICATE OF COMPLETION   ★")

        # Main Title
        c.setFont("Helvetica-Bold", 30)
        c.setFillColor(self.NAVY_PRIMARY)
        c.drawCentredString(w / 2, h - 130, "CERTIFICATE OF ACHIEVEMENT")

        # Decorative Divider
        c.setStrokeColor(self.GOLD_ACCENT)
        c.setLineWidth(1.5)
        c.line(w / 2 - 140, h - 145, w / 2 + 140, h - 145)

        c.setFillColor(self.GOLD_ACCENT)
        c.circle(w / 2, h - 145, 3, fill=True, stroke=False)

    def _draw_recipient(self, c: canvas.Canvas, recipient_name: str) -> None:
        """Draw recipient presentation text and prominent recipient name."""
        w, h = self.PAGE_WIDTH, self.PAGE_HEIGHT

        # Presentation phrase
        c.setFont("Helvetica", 12)
        c.setFillColor(self.SLATE_GRAY)
        c.drawCentredString(w / 2, h - 195, "THIS IS PROUDLY PRESENTED TO")

        # Recipient Name
        c.setFont("Helvetica-Bold", 32)
        c.setFillColor(self.NAVY_PRIMARY)
        c.drawCentredString(w / 2, h - 245, recipient_name)

        # Underline accent
        name_width = min(c.stringWidth(recipient_name, "Helvetica-Bold", 32) + 60, 420)
        c.setStrokeColor(self.GOLD_ACCENT)
        c.setLineWidth(1.2)
        c.line(w / 2 - name_width / 2, h - 258, w / 2 + name_width / 2, h - 258)

    def _draw_course_info(self, c: canvas.Canvas, certificate_title: str) -> None:
        """Draw course / achievement title and completion statement."""
        w, h = self.PAGE_WIDTH, self.PAGE_HEIGHT

        c.setFont("Helvetica", 12)
        c.setFillColor(self.SLATE_GRAY)
        c.drawCentredString(
            w / 2,
            h - 295,
            "for successfully completing and fulfilling all requirements of the program",
        )

        # Certificate Title / Program Name
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(self.NAVY_PRIMARY)
        c.drawCentredString(w / 2, h - 330, certificate_title)

    def _draw_footer(
        self,
        c: canvas.Canvas,
        certificate_date: Union[date, str],
        certificate_id: str,
    ) -> None:
        """Draw verification metadata, date, signature line, and decorative badge."""
        w, _ = self.PAGE_WIDTH, self.PAGE_HEIGHT
        date_str = certificate_date.isoformat() if isinstance(certificate_date, date) else str(certificate_date)

        # Left: Issue Date
        c.setStrokeColor(self.SLATE_GRAY)
        c.setLineWidth(0.8)
        c.line(100, 115, 250, 115)

        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(self.TEXT_DARK)
        c.drawCentredString(175, 122, date_str)

        c.setFont("Helvetica", 9)
        c.setFillColor(self.SLATE_GRAY)
        c.drawCentredString(175, 100, "ISSUE DATE")

        # Center: Golden Credential Seal
        c.setFillColor(self.GOLD_LIGHT)
        c.setStrokeColor(self.GOLD_ACCENT)
        c.setLineWidth(2)
        c.circle(w / 2, 115, 30, fill=True, stroke=True)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(self.NAVY_PRIMARY)
        c.drawCentredString(w / 2, 120, "VERIFIED")
        c.drawCentredString(w / 2, 108, "HONOR")

        # Right: Signature & Certificate ID
        c.setStrokeColor(self.SLATE_GRAY)
        c.setLineWidth(0.8)
        c.line(w - 250, 115, w - 100, 115)

        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(self.TEXT_DARK)
        c.drawCentredString(w - 175, 122, "Authorized Signature")

        c.setFont("Helvetica", 9)
        c.setFillColor(self.SLATE_GRAY)
        c.drawCentredString(w - 175, 100, "PROGRAM DIRECTOR")

        # Bottom Bar: Unique Credential ID
        c.setFont("Helvetica", 8)
        c.setFillColor(self.SLATE_GRAY)
        c.drawCentredString(
            w / 2,
            55,
            f"Unique Credential ID: {certificate_id}   •   Verified & Issued via Certificate Engine",
        )

    def generate_pdf_bytes(
        self,
        recipient_name: str,
        certificate_title: str,
        certificate_date: Union[date, str],
        certificate_id: str,
    ) -> bytes:
        """Render the complete certificate to an in-memory PDF byte buffer."""
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(letter))
        c.setTitle(f"Certificate - {recipient_name}")

        self._draw_borders(c)
        self._draw_header(c)
        self._draw_recipient(c, recipient_name)
        self._draw_course_info(c, certificate_title)
        self._draw_footer(c, certificate_date, certificate_id)

        c.showPage()
        c.save()

        buffer.seek(0)
        return buffer.getvalue()

    def generate_and_save(
        self,
        job_id: Union[uuid.UUID, str],
        certificate_db_id: Union[uuid.UUID, str],
        recipient_name: str,
        certificate_title: str,
        certificate_date: Union[date, str],
        certificate_id: str,
    ) -> Path:

        
        """Generate PDF certificate and write it directly to persistent storage."""
        pdf_bytes = self.generate_pdf_bytes(
            recipient_name=recipient_name,
            certificate_title=certificate_title,
            certificate_date=certificate_date,
            certificate_id=certificate_id,
        )
        return storage_service.save_certificate_file(
            job_id=job_id,
            certificate_id=certificate_db_id,
            content=pdf_bytes,
        )


certificate_service = CertificateService()
