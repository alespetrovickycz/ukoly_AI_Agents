"""PDF report generator for Wazuh incident analysis."""
import os
from io import BytesIO
from typing import Dict, Any
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Image, Paragraph, Spacer, Table,
    TableStyle, PageBreak
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Set matplotlib to use non-interactive backend
matplotlib.use('Agg')

# Set seaborn style
sns.set_style("whitegrid")

# Register Unicode font for Czech characters
try:
    pdfmetrics.registerFont(TTFont('DejaVuSans', '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', '/usr/share/fonts/dejavu-sans-fonts/DejaVuSans-Bold.ttf'))
    FONT_NAME = 'DejaVuSans'
    FONT_NAME_BOLD = 'DejaVuSans-Bold'
except Exception as e:
    # Fallback to Helvetica if DejaVu not available
    print(f"Warning: Could not load DejaVu fonts: {e}")
    FONT_NAME = 'Helvetica'
    FONT_NAME_BOLD = 'Helvetica-Bold'


def create_timeline_chart(timeline_df: pd.DataFrame) -> BytesIO:
    """Create line chart showing daily incident trend."""
    fig, ax = plt.subplots(figsize=(10, 5))

    ax.plot(timeline_df['date'], timeline_df['count'], marker='o', linewidth=2, color='steelblue')
    ax.fill_between(timeline_df['date'], timeline_df['count'], alpha=0.3, color='steelblue')

    ax.set_title('Časová osa incidentů', fontsize=14, fontweight='bold')
    ax.set_xlabel('Datum')
    ax.set_ylabel('Počet incidentů')
    ax.grid(True, alpha=0.3)

    # Rotate x-axis labels
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_severity_chart(severity_data: Dict[str, int]) -> BytesIO:
    """Create bar chart with color-coded severity levels."""
    if not severity_data:
        # Return empty chart if no data
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.text(0.5, 0.5, 'Žádná data', ha='center', va='center', fontsize=14)
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    fig, ax = plt.subplots(figsize=(10, 5))

    # Convert keys to integers and sort
    # OpenSearch returns keys as integers, but they might be stored as strings
    level_count_pairs = [(int(k) if isinstance(k, str) else k, v) for k, v in severity_data.items()]
    level_count_pairs.sort(key=lambda x: x[0])

    levels = [pair[0] for pair in level_count_pairs]
    counts = [pair[1] for pair in level_count_pairs]

    # Color gradient: green (low) to red (critical)
    color_map = []
    for level in levels:
        if level <= 5:
            color_map.append('green')
        elif level <= 9:
            color_map.append('yellow')
        else:
            color_map.append('red')

    ax.bar(levels, counts, color=color_map, alpha=0.7, edgecolor='black')
    ax.set_title('Distribuce podle závažnosti', fontsize=14, fontweight='bold')
    ax.set_xlabel('Úroveň závažnosti')
    ax.set_ylabel('Počet incidentů')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_top_items_chart(data: Dict[str, int], title: str, max_items: int = 10) -> BytesIO:
    """Create horizontal bar chart for top N items."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Get top N items
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)[:max_items]
    labels = [item[0] for item in items]
    values = [item[1] for item in items]

    # Reverse for horizontal bar (highest at top)
    labels.reverse()
    values.reverse()

    ax.barh(labels, values, color='steelblue', alpha=0.8)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Počet incidentů')
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def create_pie_chart(data: Dict[str, int], title: str, max_items: int = 8) -> BytesIO:
    """Create pie chart for distribution."""
    if not data:
        # Return empty chart if no data
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.text(0.5, 0.5, 'Žádná data', ha='center', va='center', fontsize=14)
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        return buf

    fig, ax = plt.subplots(figsize=(10, 8))

    # Get top N items, group rest as "Ostatní"
    # Filter out "N/A" from top items if there are enough real values
    items = sorted(data.items(), key=lambda x: x[1], reverse=True)

    # Separate N/A from real data
    na_item = None
    real_items = []
    for item in items:
        if item[0] == "N/A":
            na_item = item
        else:
            real_items.append(item)

    # If we have enough real items, show them and optionally N/A
    if len(real_items) > max_items:
        top_items = real_items[:max_items]
        other_count = sum(item[1] for item in real_items[max_items:])
        top_items.append(("Ostatní", other_count))
    else:
        top_items = real_items.copy()

    # Add N/A at the end if it exists
    if na_item and na_item[1] > 0:
        top_items.append(na_item)

    labels = [item[0] for item in top_items]
    values = [item[1] for item in top_items]

    # Create pie chart
    wedges, texts, autotexts = ax.pie(
        values,
        labels=labels,
        autopct='%1.1f%%',
        startangle=90,
        colors=sns.color_palette("husl", len(labels))
    )

    # Make percentage text more readable
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontweight('bold')

    ax.set_title(title, fontsize=14, fontweight='bold')

    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig)
    return buf


def extract_recommendations(analysis_text: str) -> Dict[str, str]:
    """Extract strategic and tactical recommendations from LLM response.

    Args:
        analysis_text: LLM-generated analysis text

    Returns:
        Dictionary with 'strategic' and 'tactical' recommendations
    """
    # Simple parsing - look for strategic and tactical sections
    strategic = ""
    tactical = ""

    lines = analysis_text.split('\n')
    current_section = None

    for line in lines:
        line_lower = line.lower()

        if "strategick" in line_lower and "doporuč" in line_lower:
            current_section = "strategic"
            continue
        elif "taktick" in line_lower and "doporuč" in line_lower:
            current_section = "tactical"
            continue
        elif "##" in line or "**" in line:
            # New section header, might switch context
            if current_section and line.strip():
                # Add the line as it might be content
                pass

        if current_section == "strategic" and line.strip():
            strategic += line + "\n"
        elif current_section == "tactical" and line.strip():
            tactical += line + "\n"

    # If parsing didn't work well, return the whole text in strategic
    if not strategic and not tactical:
        return {"strategic": analysis_text, "tactical": ""}

    return {
        "strategic": strategic.strip(),
        "tactical": tactical.strip()
    }


def generate_pdf_report(
    incident_data: Dict[str, Any],
    analysis: str,
    output_file: str = "wazuh_report.pdf",
    logo_path: str = "./logo-full-color-cropped.png"
):
    """Generate complete Czech PDF report with company logo.

    Args:
        incident_data: Structured incident data from analyzer
        analysis: LLM-generated analysis and recommendations
        output_file: Path to output PDF file
        logo_path: Path to company logo image
    """
    doc = SimpleDocTemplate(output_file, pagesize=A4,
                          leftMargin=2*cm, rightMargin=2*cm,
                          topMargin=2*cm, bottomMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()

    # Create custom styles with Unicode font
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontName=FONT_NAME_BOLD,
        fontSize=18,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=30,
        alignment=TA_CENTER
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontName=FONT_NAME_BOLD,
        fontSize=14,
        textColor=colors.HexColor('#1f4788'),
        spaceAfter=12,
        spaceBefore=12
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontName=FONT_NAME,
        fontSize=10
    )

    # 1. Logo and Title
    if os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=6*cm, height=1*cm)
            logo.hAlign = 'RIGHT'
            story.append(logo)
            story.append(Spacer(1, 0.5*cm))
        except Exception as e:
            print(f"Warning: Could not load logo: {e}")

    # Get date range from query info
    query_info = incident_data.get("query_info", {})
    start_date = query_info.get("start_date", "N/A")[:10]  # YYYY-MM-DD
    end_date = query_info.get("end_date", "N/A")[:10]

    title = Paragraph(
        f"<b>Report bezpečnostních incidentů Wazuh</b><br/>{start_date} až {end_date}",
        title_style
    )
    story.append(title)
    story.append(Spacer(1, 1*cm))

    # 2. Executive Summary Table
    stats = incident_data["statistics"]

    summary_data = [
        ['Metrika', 'Hodnota'],
        ['Celkový počet incidentů', str(stats['total_incidents'])],
        ['Denní průměr', f"{stats['daily_average']}"],
        ['Kritické incidenty (úroveň >9)', str(stats['critical_count'])],
        ['Země - největší zdroj incidentů', stats['top_country']],
        ['Nejčastější typ incidentu', stats['top_incident_type']],
        ['Nejaktivnější útočící IP', f"{stats['top_srcip']} ({stats['top_srcip_count']} útoků)"]
    ]

    table = Table(summary_data, colWidths=[10*cm, 6*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f4788')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), FONT_NAME_BOLD),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('FONTNAME', (0, 1), (-1, -1), FONT_NAME),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
    ]))
    story.append(table)
    story.append(Spacer(1, 1*cm))

    # 3. Timeline Chart
    story.append(Paragraph("Časová osa incidentů", heading_style))
    timeline_img = Image(
        create_timeline_chart(incident_data["aggregations"]["timeline"]),
        width=16*cm, height=8*cm
    )
    story.append(timeline_img)
    story.append(Spacer(1, 0.5*cm))

    # 4. Severity Distribution
    story.append(Paragraph("Distribuce podle závažnosti", heading_style))
    severity_img = Image(
        create_severity_chart(incident_data["aggregations"]["severity"]),
        width=16*cm, height=8*cm
    )
    story.append(severity_img)
    story.append(Spacer(1, 0.5*cm))

    # Page break
    story.append(PageBreak())

    # 5. Top 10 Incident Types
    story.append(Paragraph("Top 10 typů incidentů", heading_style))
    types_img = Image(
        create_top_items_chart(incident_data["aggregations"]["types"], "Top 10 typů incidentů"),
        width=16*cm, height=10*cm
    )
    story.append(types_img)
    story.append(Spacer(1, 0.5*cm))

    # 6. Country Distribution (Pie Chart)
    story.append(Paragraph("Distribuce podle zemí", heading_style))
    region_img = Image(
        create_pie_chart(incident_data["aggregations"]["regions"], "Distribuce podle zemí"),
        width=16*cm, height=13*cm
    )
    story.append(region_img)

    # Page break
    story.append(PageBreak())

    # 7. Top Servers/Agents
    story.append(Paragraph("Top 10 serverů podle počtu incidentů", heading_style))
    agent_img = Image(
        create_top_items_chart(incident_data["aggregations"]["agents"], "Top 10 serverů"),
        width=16*cm, height=10*cm
    )
    story.append(agent_img)
    story.append(Spacer(1, 0.5*cm))

    # 8. Top útočících IP adres
    story.append(Paragraph("Top 20 útočících IP adres", heading_style))
    srcip_img = Image(
        create_top_items_chart(incident_data["aggregations"]["srcips"], "Top 20 útočících IP adres", max_items=20),
        width=16*cm, height=12*cm
    )
    story.append(srcip_img)
    story.append(Spacer(1, 0.5*cm))

    # 9. Top Decoders
    story.append(Paragraph("Top 10 dekoderů", heading_style))
    decoder_img = Image(
        create_top_items_chart(incident_data["aggregations"]["decoders"], "Top 10 dekoderů"),
        width=16*cm, height=10*cm
    )
    story.append(decoder_img)

    # Page break before recommendations
    story.append(PageBreak())

    # 9. AI Recommendations
    story.append(Paragraph("Doporučení pro snížení počtu incidentů", title_style))
    story.append(Spacer(1, 0.5*cm))

    recommendations = extract_recommendations(analysis)

    # Helper function to convert markdown bold to HTML
    def markdown_to_html(text: str) -> str:
        """Convert markdown bold (**text**) to HTML (<b>text</b>)."""
        import re
        # Replace **text** with <b>text</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        # Replace newlines with <br/>
        text = text.replace('\n', '<br/>')
        return text

    if recommendations["strategic"]:
        story.append(Paragraph("Strategická doporučení", heading_style))
        story.append(Paragraph(
            markdown_to_html(recommendations["strategic"]),
            normal_style
        ))
        story.append(Spacer(1, 0.5*cm))

    if recommendations["tactical"]:
        story.append(Paragraph("Taktická a technická doporučení", heading_style))
        story.append(Paragraph(
            markdown_to_html(recommendations["tactical"]),
            normal_style
        ))

    # If no clear separation, just add the whole analysis
    if not recommendations["strategic"] and not recommendations["tactical"]:
        story.append(Paragraph(
            markdown_to_html(analysis),
            normal_style
        ))

    # Build PDF
    doc.build(story)
    print(f"✅ Report vygenerován: {output_file}")
