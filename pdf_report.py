import io
import time
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.services.firestore_client import firestore_client
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
import httpx
from io import BytesIO

router = APIRouter(prefix="/api/reports", tags=["PDF Reports"])

@router.get("/{incident_id}/pdf")
async def generate_incident_pdf(incident_id: str):
    # Fetch incident from firestore
    try:
        doc = firestore_client.db.collection('incidents').document(incident_id).get()
        if not doc.exists:
            raise HTTPException(status_code=404, detail="Incident not found")
        incident = doc.to_dict()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    buffer = io.BytesIO()
    doc_template = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    normal_style = styles['Normal']
    
    custom_title = ParagraphStyle(
        'CustomTitle',
        parent=title_style,
        fontSize=18,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14
    )
    
    elements = []
    
    # Header
    elements.append(Paragraph("<b>Metropolis City Command</b> - Official Incident Report", custom_title))
    elements.append(Paragraph(f"<b>Incident ID:</b> {incident_id}", normal_style))
    elements.append(Paragraph(f"<b>Generated At:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    elements.append(Spacer(1, 12))
    
    # Image downloading and embedding
    image_url = incident.get("image_url")
    if image_url:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(image_url)
                if resp.status_code == 200:
                    img_data = BytesIO(resp.content)
                    img = Image(img_data, width=400, height=300)
                    elements.append(img)
                    elements.append(Spacer(1, 12))
        except Exception as e:
            elements.append(Paragraph(f"<i>(Failed to load incident image: {e})</i>", normal_style))
            elements.append(Spacer(1, 12))
            
    # AI Analysis & Core Data
    elements.append(Paragraph("<b>Analysis & Priority</b>", styles['Heading2']))
    
    analysis = incident.get("analysis", {})
    decision = analysis.get("decision", {})
    
    data = [
        ["Category", decision.get("category", "Unknown")],
        ["Status", incident.get("status", "Unknown")],
        ["Priority Score", str(decision.get("priority", 0)) + "/100"],
        ["AI Confidence", str(incident.get("ai_confidence", 0)) + "%"],
        ["Location", f"{incident.get('lat', 0)}, {incident.get('lng', 0)}"],
        ["Street Name", incident.get("street_name", "Unknown")]
    ]
    
    table = Table(data, colWidths=[150, 300])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor("#0f172a")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1"))
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 12))
    
    # Summary
    elements.append(Paragraph("<b>AI Summary</b>", styles['Heading3']))
    elements.append(Paragraph(analysis.get("summary", "No summary available."), normal_style))
    elements.append(Spacer(1, 12))
    
    # History
    elements.append(Paragraph("<b>Incident History</b>", styles['Heading3']))
    history = incident.get("merge_history", [])
    if history:
        for entry in history:
            ts = entry.get("timestamp")
            action = entry.get("action", "Unknown Action")
            elements.append(Paragraph(f"• {action}", normal_style))
    else:
        elements.append(Paragraph("No history recorded.", normal_style))

    # Build PDF
    doc_template.build(elements)
    
    buffer.seek(0)
    return StreamingResponse(
        buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"inline; filename=incident_{incident_id}.pdf"}
    )
