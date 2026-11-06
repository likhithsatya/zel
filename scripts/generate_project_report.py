#!/usr/bin/env python3
"""Generate the editable v1 project report and architecture PDF."""

import argparse
from datetime import datetime, timezone
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "docs"
TITLE = "HGX B300 Custom Ubuntu Installer"
SUBTITLE = "Version 1 build, architecture, and test report"
RELEASE_URL = "https://github.com/likhithsatya/zel/releases/tag/b300-ubuntu-24.04.3-r620-20261106"
ISO_NAME = "nvidia-b300-ubuntu-24.04.3-r620.iso"
ISO_SHA256 = "be8d2af941a072a5428c0ab8ed0c49f3eb248672542f56b4127d2ae557db52f9"
REPORT_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d UTC")

SECTIONS = [
    ("heading", "Executive summary"),
    (
        "paragraph",
        "V1 is a bootable Ubuntu Server 24.04.3 installer ISO for a supervised B300 test. "
        "It installs the NVIDIA R620 driver candidate, CUDA 13.5, and Fabric Manager during "
        "Autoinstall. The image is prepared and UEFI-boot-smoke-tested in QEMU; it has not been "
        "installed on the physical B300 and its GPU stack is not hardware-validated.",
    ),
    ("heading", "Architecture"),
    ("diagram", None),
    (
        "paragraph",
        "The report shows two distinct paths. The original POC path is NICo with UEFI HTTP/iPXE "
        "and a NICo-hosted NoCloud seed. The V1 custom ISO is booted using the operator's chosen "
        "media method and does not register with or call NICo. BMC handling is operator-owned and "
        "was not performed by this project.",
    ),
    ("heading", "What was built"),
    (
        "bullets",
        [
            "Ubuntu 24.04.3 source ISO verified against Ubuntu's signed SHA256 manifest.",
            "Custom ISO remaster preserving BIOS and UEFI boot metadata, with local NoCloud seed and Autoinstall arguments.",
            "Interactive identity, disk/storage, and SSH setup; no disk serial or SSH key is baked into the image.",
            "Late-command installs the pinned candidate NVIDIA stack from Ubuntu/NVIDIA repositories; network access is required during installation.",
            "Build scripts, self-hosted GitHub Actions workflow, QEMU/OVMF smoke test, checksum/manifest, and GitHub release packaging split under the per-asset size limit.",
        ],
    ),
    ("heading", "V1 software candidate"),
    (
        "table",
        [
            ["Component", "Pinned package(s)", "Status"],
            ["NVIDIA driver", "nvidia-open 620.70.06-1ubuntu1; pin package 620.70.06-1ubuntu1", "Candidate; not B300-tested"],
            ["CUDA Toolkit", "cuda-toolkit-13-5 13.5.0-1", "Candidate; repository dependencies are version-ranged"],
            ["Fabric Manager", "nvidia-fabricmanager 620-1 -> direct 2.0.0.rel106-1", "Standalone FM versioning for R620"],
            ["FM driver library", "libnvidia-fmdrv1 620.70.06-1ubuntu1", "Pinned to matching driver package"],
        ],
    ),
    (
        "paragraph",
        "NVIDIA's R620 release notes mention HGX B300 and Ubuntu 24.04, and the Fabric Manager "
        "guide documents HGX B300 NVSwitch topology and independent FM versioning starting at "
        "driver release 620. These references do not constitute qualification of the exact "
        "Supermicro PIO-422GS-NB3RT. R620.70.06 was released on 2026-11-04 and is a new branch. "
        "NVIDIA's R595 branch (595.112.07, released 2026-10-22) is an older alternative, not the "
        "stack in this V1 ISO; neither branch is OEM-qualified for this exact server.",
    ),
    ("heading", "Test evidence"),
    (
        "bullets",
        [
            "8 local unit tests pass, including Autoinstall/GRUB behavior, release split/reassembly, report generation, manifest integrity, and default installer gates.",
            "Ubuntu source signature and ISO checksum verified; custom ISO checksum verified.",
            "QEMU with OVMF boots the ISO to Ubuntu 24.04.3 kernel and confirms local Autoinstall arguments. No virtual disk was attached.",
            "The custom ISO was built locally. The self-hosted GitHub image workflow is configured but has not yet been run.",
            "No complete VM installation, NVIDIA package download/install, physical B300 install, or GPU/NVSwitch validation has been performed.",
        ],
    ),
    ("heading", "Release"),
    (
        "paragraph",
        f"ISO: {ISO_NAME}. SHA256: {ISO_SHA256}. GitHub Release: {RELEASE_URL}. "
        "The ISO is split into two downloadable parts because GitHub limits individual release "
        "assets to under 2 GiB. Download every release asset into one directory and run "
        "bash assemble-release-iso.sh . to reconstruct and verify the ISO. The GitHub repository "
        "is private, so release access is limited to repository collaborators.",
    ),
    ("heading", "Before physical testing"),
    (
        "numbered",
        [
            "Get fresh written disk-wipe approval and a dated install window; the previous POC approval does not cover this run. Likhith and Sai Rishith are the proposed test operators; schedule is pending Chakra/owner confirmation.",
            "Confirm with the NICo credential custodian how the BIOS setup password is obtained and whether current lockdown/boot settings permit the selected ISO boot method. Do not bypass lockdown or change firmware settings without authorization.",
            "If using BMC virtual media, verify the media session survives reboot/link interruptions. The tracker reports brief BMC network drops; that this could interrupt virtual-media boot is a risk to check, not a proven failure.",
            "Agree on rollback before starting: console access, recovery media or approved NICo reprovisioning route, and how to reconcile the host back to NICo Ready. No rollback has been tested.",
            "Select and verify the intended disk at the interactive installer storage screen; supervise the console.",
            "Check Secure Boot/MOK requirements and confirm VLAN 30 can reach Ubuntu and NVIDIA package repositories or an approved mirror.",
            "Coordinate the NICo record update because this ISO boot path bypasses NICo; no BMC/NICo action was performed by this project.",
            "After installation, validate OS/SSH, then driver, all eight GPU PCI devices, nvidia-smi, CUDA, and Fabric Manager on the physical B300. Keep results separate from the QEMU smoke-test result.",
        ],
    ),
    ("heading", "Scope boundary"),
    (
        "paragraph",
        "This is an installer ISO, not a preinstalled raw/qcow2 image or a named Hydra-like custom "
        "image. The PXE/NICo workflow remains available separately. No BMC operation, NICo "
        "registration, disk wipe, physical installation, or GPU qualification was performed.",
    ),
]


def markdown_source() -> str:
    lines = [
        f"# {TITLE} — {SUBTITLE}",
        "",
        f"**Generated:** {REPORT_DATE}",
        "**Status:** Prepared for supervised test; physical B300/GPU validation pending.",
        "",
        "```mermaid",
        "flowchart LR",
        '  A[Official Ubuntu 24.04.3 ISO] --> B[Verify signature and SHA256] --> C[Remaster GRUB + local seed + NVIDIA tools] --> D[Custom UEFI/BIOS ISO] --> E[Interactive Autoinstall] --> F[Ubuntu + NVIDIA candidate stack]',
        '  N[NICo controller] --> R[Existing VLAN 30 DHCP relay] --> I[UEFI HTTP / iPXE] --> S[Ubuntu assets + tenant-cloudinit-url seed] --> P[POC Autoinstall path]',
        "```",
        "",
        "The custom ISO path is distinct from the original NICo/iPXE POC path. The ISO does not register with NICo; BMC handling is operator-owned.",
        "",
    ]
    for kind, content in SECTIONS:
        if kind == "heading":
            lines.extend([f"## {content}", ""])
        elif kind == "paragraph":
            lines.extend([content, ""])
        elif kind == "bullets":
            lines.extend([f"- {item}" for item in content])
            lines.append("")
        elif kind == "numbered":
            lines.extend([f"{index}. {item}" for index, item in enumerate(content, 1)])
            lines.append("")
        elif kind == "table":
            lines.append("| " + " | ".join(content[0]) + " |")
            lines.append("| " + " | ".join("---" for _ in content[0]) + " |")
            lines.extend("| " + " | ".join(row) + " |" for row in content[1:])
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


class ArchitectureDiagram(Flowable):
    def __init__(self):
        super().__init__()
        self.height = 2.55 * inch

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        box_width = (self.width - 4 * 8) / 5
        box_height = 54
        rows = [
            (
                "CUSTOM ISO V1",
                [
                    "Verified Ubuntu\n24.04.3 ISO",
                    "Remaster: GRUB,\nseed, NVIDIA tools",
                    "UEFI/BIOS boot\nfrom ISO",
                    "Interactive\nAutoinstall",
                    "NVIDIA repo:\ndriver + FM + CUDA",
                ],
            ),
            (
                "REFERENCE NICo PXE PATH",
                [
                    "NICo controller",
                    "Existing VLAN 30\nDHCP relay",
                    "UEFI HTTP\nthen iPXE",
                    "Ubuntu media +\nNoCloud seed URL",
                    "POC Autoinstall\n(no GPU stack)",
                ],
            ),
        ]
        for row_index, (label, boxes) in enumerate(rows):
            y = self.height - (row_index + 1) * 86
            self.canv.setFont("Helvetica-Bold", 8)
            self.canv.setFillColor(colors.HexColor("#344054"))
            self.canv.drawString(0, y + box_height + 8, label)
            for index, text in enumerate(boxes):
                x = index * (box_width + 8)
                self.canv.setFillColor(colors.HexColor("#EFF4FA" if row_index == 0 else "#F4F6F8"))
                self.canv.setStrokeColor(colors.HexColor("#7C8DA5"))
                self.canv.roundRect(x, y, box_width, box_height, 5, fill=1, stroke=1)
                self.canv.setFillColor(colors.HexColor("#172B4D"))
                self.canv.setFont("Helvetica", 7.3)
                for line_index, line in enumerate(text.split("\n")):
                    self.canv.drawCentredString(x + box_width / 2, y + box_height / 2 + 5 - 10 * line_index, line)
                if index < len(boxes) - 1:
                    arrow_start = x + box_width + 1
                    arrow_end = x + box_width + 7
                    mid_y = y + box_height / 2
                    self.canv.setStrokeColor(colors.HexColor("#475467"))
                    self.canv.line(arrow_start, mid_y, arrow_end, mid_y)
                    self.canv.line(arrow_end, mid_y, arrow_end - 3, mid_y + 3)
                    self.canv.line(arrow_end, mid_y, arrow_end - 3, mid_y - 3)


def build_pdf(path: Path):
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=22, leading=27, textColor=colors.HexColor("#16324F"), alignment=TA_CENTER, spaceAfter=6))
    styles.add(ParagraphStyle(name="ReportSubtitle", parent=styles["Normal"], fontSize=11, leading=15, textColor=colors.HexColor("#475467"), alignment=TA_CENTER, spaceAfter=10))
    styles.add(ParagraphStyle(name="SectionHeading", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13, leading=16, textColor=colors.HexColor("#16324F"), spaceBefore=9, spaceAfter=5, keepWithNext=True))
    styles.add(ParagraphStyle(name="BodySmall", parent=styles["BodyText"], fontSize=8.5, leading=11.3, spaceAfter=5))
    styles.add(ParagraphStyle(name="BulletSmall", parent=styles["BodyText"], fontSize=8.3, leading=10.6, leftIndent=12, firstLineIndent=-8, bulletIndent=0, spaceAfter=2.5))
    styles.add(ParagraphStyle(name="TableHead", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.6, leading=9, textColor=colors.white))
    styles.add(ParagraphStyle(name="TableBody", parent=styles["BodyText"], fontSize=7.4, leading=9))
    page_width, page_height = letter
    doc = SimpleDocTemplate(
        str(path), pagesize=letter, rightMargin=0.55 * inch, leftMargin=0.55 * inch,
        topMargin=0.58 * inch, bottomMargin=0.58 * inch,
        title=f"{TITLE} - V1 Build and Test Report",
        author="B300 Ubuntu Custom Installer Project",
    )
    story = [
        Spacer(1, 0.1 * inch),
        Paragraph(TITLE, styles["ReportTitle"]),
        Paragraph(SUBTITLE, styles["ReportSubtitle"]),
        Paragraph(f"Generated {REPORT_DATE} &nbsp; | &nbsp; Prepared for supervised test &nbsp; | &nbsp; Physical B300 validation pending", styles["BodySmall"]),
        Spacer(1, 5),
    ]
    for kind, content in SECTIONS:
        if kind == "heading":
            story.append(Paragraph(content, styles["SectionHeading"]))
        elif kind == "paragraph":
            story.append(Paragraph(content, styles["BodySmall"]))
        elif kind == "diagram":
            story.append(ArchitectureDiagram())
            story.append(Spacer(1, 4))
        elif kind in ("bullets", "numbered"):
            for index, item in enumerate(content, 1):
                prefix = f"{index}." if kind == "numbered" else "•"
                story.append(Paragraph(f"{prefix} &nbsp; {item}", styles["BulletSmall"]))
        elif kind == "table":
            rows = []
            for row_index, row in enumerate(content):
                style = styles["TableHead"] if row_index == 0 else styles["TableBody"]
                rows.append([Paragraph(value, style) for value in row])
            table = Table(rows, colWidths=[1.05 * inch, 2.65 * inch, 2.65 * inch], repeatRows=1, hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324F")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#F4F6F8")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D0D5DD")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]))
            story.extend([table, Spacer(1, 5)])

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor("#D0D5DD"))
        canvas.line(doc.leftMargin, 0.43 * inch, page_width - doc.rightMargin, 0.43 * inch)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#667085"))
        canvas.drawString(doc.leftMargin, 0.27 * inch, "B300 Custom Ubuntu Installer V1 | Not hardware validated")
        canvas.drawRightString(page_width - doc.rightMargin, 0.27 * inch, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = args.output_dir / "B300-CUSTOM-OS-V1-REPORT.md"
    pdf_path = args.output_dir / "B300-CUSTOM-OS-V1-REPORT.pdf"
    markdown_path.write_text(markdown_source(), encoding="utf-8")
    build_pdf(pdf_path)
    print(f"Report source: {markdown_path}")
    print(f"Architecture report: {pdf_path}")


if __name__ == "__main__":
    main()