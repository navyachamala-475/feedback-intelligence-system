
import logging
import os
import io
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

def generate_pdf_report(df, issue_summary, trend_data, output_path,
                         app_name="App", company="ProductTeam"):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table,
            TableStyle, HRFlowable, PageBreak,
        )
        from reportlab.lib.enums import TA_CENTER

        DARK   = colors.HexColor("#0F172A")
        ACCENT = colors.HexColor("#3B82F6")
        GREEN  = colors.HexColor("#10B981")
        RED    = colors.HexColor("#EF4444")
        LIGHT  = colors.HexColor("#F1F5F9")
        WHITE  = colors.white

        styles  = getSampleStyleSheet()
        h1      = ParagraphStyle("H1", parent=styles["Title"], fontSize=26,
                                  textColor=DARK, spaceAfter=4, fontName="Helvetica-Bold")
        h2      = ParagraphStyle("H2", parent=styles["Heading1"], fontSize=14,
                                  textColor=ACCENT, spaceBefore=12, spaceAfter=4,
                                  fontName="Helvetica-Bold")
        body    = ParagraphStyle("Body", parent=styles["Normal"], fontSize=10,
                                  textColor=DARK, leading=14)
        caption = ParagraphStyle("Caption", parent=styles["Normal"], fontSize=8,
                                  textColor=colors.HexColor("#64748B"), alignment=TA_CENTER)
        small   = ParagraphStyle("Small", parent=styles["Normal"], fontSize=9,
                                  textColor=colors.HexColor("#475569"))

        doc   = SimpleDocTemplate(output_path, pagesize=A4,
                                   leftMargin=2*cm, rightMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
        story = []
        today = datetime.now().strftime("%B %d, %Y")

        story.append(Paragraph("Feedback Intelligence Report", h1))
        story.append(Paragraph(f"{app_name} | Week ending {today} | {company}", small))
        story.append(HRFlowable(width="100%", thickness=2, color=ACCENT, spaceAfter=12))
        story.append(Paragraph("Executive Summary", h2))

        if not df.empty:
            total    = len(df)
            avg_r    = df["rating"].mean()
            pos_pct  = (df["sentiment_label"]=="Positive").sum()/total*100
            neg_pct  = (df["sentiment_label"]=="Negative").sum()/total*100
            sources  = ", ".join(df["source"].unique())
            critical = issue_summary[issue_summary["is_critical"]==True] if not issue_summary.empty else pd.DataFrame()

            story.append(Paragraph(
                f"This report covers <b>{total:,} reviews</b> from <b>{sources}</b>. "
                f"Average rating: <b>{avg_r:.2f}/5.0</b>. "
                f"Sentiment: <b>{pos_pct:.1f}%</b> positive, <b>{neg_pct:.1f}%</b> negative. "
                f"<b>{len(critical)}</b> critical issues identified.",
                body
            ))
            story.append(Spacer(1, 12))

            kpi_data = [
                ["Metric",           "Value"],
                ["Total Reviews",    f"{total:,}"],
                ["Average Rating",   f"{avg_r:.2f} / 5.0"],
                ["Positive Reviews", f"{(df['sentiment_label']=='Positive').sum():,} ({pos_pct:.1f}%)"],
                ["Negative Reviews", f"{(df['sentiment_label']=='Negative').sum():,} ({neg_pct:.1f}%)"],
                ["Critical Issues",  f"{len(critical)}"],
                ["Data Sources",     str(df['source'].nunique())],
            ]
            kpi_table = Table(kpi_data, colWidths=[8*cm, 8*cm])
            kpi_table.setStyle(TableStyle([
                ("BACKGROUND",    (0,0), (-1,0), ACCENT),
                ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
                ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                ("FONTSIZE",      (0,0), (-1,-1), 10),
                ("ROWBACKGROUNDS",(0,1), (-1,-1), [WHITE, LIGHT]),
                ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING",       (0,0), (-1,-1), 8),
            ]))
            story.append(kpi_table)
            story.append(Spacer(1, 16))

        story.append(Paragraph("Critical Issues", h2))
        if not issue_summary.empty:
            critical = issue_summary[issue_summary["is_critical"]==True]
            if not critical.empty:
                issue_rows = [["Issue Category","Mentions","Neg. Ratio","Avg Sentiment"]]
                for _, row in critical.iterrows():
                    issue_rows.append([
                        row["category"],
                        str(int(row["mention_count"])),
                        f"{row['neg_ratio']*100:.1f}%",
                        f"{row['avg_sentiment']:.3f}",
                    ])
                issue_table = Table(issue_rows, colWidths=[7*cm,3*cm,3*cm,3*cm])
                issue_table.setStyle(TableStyle([
                    ("BACKGROUND",    (0,0), (-1,0), RED),
                    ("TEXTCOLOR",     (0,0), (-1,0), WHITE),
                    ("FONTNAME",      (0,0), (-1,0), "Helvetica-Bold"),
                    ("FONTSIZE",      (0,0), (-1,-1), 9),
                    ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#FEF2F2"), WHITE]),
                    ("GRID",          (0,0), (-1,-1), 0.5, colors.HexColor("#FECACA")),
                    ("PADDING",       (0,0), (-1,-1), 7),
                ]))
                story.append(issue_table)
            else:
                story.append(Paragraph("No critical issues detected.", body))

        story.append(Spacer(1, 16))
        story.append(Paragraph("Notable Reviews", h2))

        if not df.empty:
            top_neg = df[df["sentiment_label"]=="Negative"].nsmallest(3,"compound")
            top_pos = df[df["sentiment_label"]=="Positive"].nlargest(3,"compound")

            story.append(Paragraph("Top Negative Reviews:", small))
            for _, r in top_neg.iterrows():
                story.append(Paragraph(
                    f"<b>[{r['source']} | ⭐{r['rating']:.0f}]</b> {str(r['body'])[:200]}...",
                    small))
                story.append(Spacer(1, 4))

            story.append(Spacer(1, 8))
            story.append(Paragraph("Top Positive Reviews:", small))
            for _, r in top_pos.iterrows():
                story.append(Paragraph(
                    f"<b>[{r['source']} | ⭐{r['rating']:.0f}]</b> {str(r['body'])[:200]}...",
                    small))
                story.append(Spacer(1, 4))

        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=ACCENT))
        story.append(Paragraph(
            f"Generated by Feedback Intelligence System | {today} | {company}",
            caption))

        doc.build(story)
        logger.info(f"PDF report saved to {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise
