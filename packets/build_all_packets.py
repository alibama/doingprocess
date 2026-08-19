import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon, Circle

EM = "\u2014"; SS = "\u00a7"; MID = "\u00b7"

styles = getSampleStyleSheet()
body = ParagraphStyle('body', parent=styles['Normal'], fontName='Helvetica',
                      fontSize=10.5, leading=14.5, spaceAfter=8, alignment=TA_LEFT)
subp = ParagraphStyle('subp', parent=body, leftIndent=14, spaceAfter=4)
head = ParagraphStyle('head', parent=styles['Normal'], fontName='Helvetica-Bold',
                      fontSize=13, leading=16, spaceAfter=10)
kicker = ParagraphStyle('kicker', parent=styles['Normal'], fontName='Helvetica-Bold',
                        fontSize=8.5, leading=11, spaceAfter=14)
quote = ParagraphStyle('quote', parent=body, fontName='Helvetica-Oblique',
                       leftIndent=18, rightIndent=18, spaceBefore=4, spaceAfter=10)
small = ParagraphStyle('small', parent=body, fontSize=9, leading=12.5, spaceAfter=6)

def letter_and_guide():
    s = []
    s.append(Paragraph("LEXIPEDIA &mdash; CONTRIBUTOR INVITATION", kicker))
    s.append(Paragraph("Dear contributor,", body))
    s.append(Paragraph(
        "Thank you for your interest in Lexipedia. Lexipedia is a free, public encyclopedia "
        "of legal <i>processes</i> &mdash; not legal advice, but plain maps of how a legal procedure "
        "works: who does what, in what order, and under which law. Everything in it is open "
        "and free for anyone to read.", body))
    s.append(Paragraph(
        "You know legal processes that most people never see up close &mdash; grievances, "
        "disciplinary hearings, appeals, records requests, parole steps. Mapping one is a real "
        "contribution, and this letter explains how to do it entirely by mail. You do not need "
        "a computer or internet.", body))
    s.append(Paragraph(
        "<b>How it works.</b> You draw a process on paper and mail it to me. I scan it, run it "
        "through our tools, and add it to the public collection, where it may be combined and "
        "cross-referenced with other maps. The page you sent is kept on file.", body))
    s.append(Paragraph("Drawing a map is explained on the next page, with a worked example. Two things matter most:", body))
    s.append(Paragraph("&mdash; Write each step as an action, and name the <b>role</b> that does it &mdash; never a specific person&rsquo;s name.", subp))
    s.append(Paragraph("&mdash; Write the law or rule number next to each step. A step without its citation cannot be used, so this is the single most important field.", subp))
    s.append(Paragraph(
        "<b>Your name and credit.</b> You are never published under your legal name. Pick a handle "
        "(any pen name) and write it on your map. When I write back, I will send you a short "
        "contributor number &mdash; please put that number on everything you send afterward, so your "
        "maps stay linked to you for credit and for our records. If you would rather show no "
        "public name at all, just write &ldquo;no public credit&rdquo;; your work still counts and is "
        "still tracked by your number. (The mailroom requires your committed name and DOC number "
        "on the envelope; I remove those before anything is published.)", body))
    s.append(Paragraph(
        "<b>Permission to publish.</b> Because everything here is free and open, I need your okay. "
        "If you agree, copy this line onto your map in your own hand and sign with your handle:", body))
    s.append(Paragraph(
        "&ldquo;I agree my contributions may be published in Lexipedia and placed in the public "
        "domain (CC0), under my handle or with no public credit, as I choose.&rdquo;", quote))
    s.append(Paragraph(
        "<b>A few practical notes.</b> This is a volunteer, educational project &mdash; there is no "
        "payment. Keep maps to plain legal procedure (boxes, arrows, rule numbers). Please do not "
        "include anything about weapons, drugs, escape, or facility security &mdash; mailroom rules "
        "will reject it. Keep it to a few standard-size pages, nothing stapled or taped.", body))
    s.append(Paragraph("If you have questions, write back. Thank you for helping make the law more legible to everyone.", body))
    s.append(Spacer(1, 10))
    s.append(Paragraph("&mdash; [Your name]", body))
    s.append(Paragraph("Lexipedia &middot; [return address]", small))
    s.append(PageBreak())
    # guide
    s.append(Paragraph("How to draw a process map", head))
    s.append(Paragraph("Use one page per process. At the top, write the process name and the system it belongs "
                       "to (for example: &ldquo;Florida inmate grievance &mdash; FDC&rdquo;). Then:", body))
    steps = [
        "Draw a box for each step. Write the step as an action: &ldquo;File informal grievance,&rdquo; &ldquo;Warden responds,&rdquo; &ldquo;Appeal to the Secretary.&rdquo;",
        "Next to each box, write the <b>role</b> that does it &mdash; inmate, warden, grievance coordinator &mdash; not a person&rsquo;s name.",
        "Next to each box, write the law or rule it comes from (a statute or rule number, for example a Florida Administrative Code rule such as 33-103). This is required.",
        "Use a diamond for a yes/no decision, with an arrow leaving each answer.",
        "If a step has a deadline, write the time next to it (&ldquo;within 15 days&rdquo;) and a small clock. Time matters in law.",
        "Draw a single circle where the process starts and a doubled circle where it ends.",
        "At the bottom, list the rulebooks or statutes you used.",
    ]
    for i, t in enumerate(steps, 1):
        s.append(Paragraph(f"{i}.&nbsp;&nbsp;{t}", subp))
    s.append(Spacer(1, 8))
    s.append(Paragraph("Shapes", ParagraphStyle('h2', parent=head, fontSize=11, spaceAfter=6)))
    s.append(Paragraph("Circle &mdash; where the process starts or ends.", subp))
    s.append(Paragraph("Rounded box &mdash; a single step (a task someone performs).", subp))
    s.append(Paragraph("Diamond &mdash; a yes/no decision; an arrow leaves each answer.", subp))
    s.append(Paragraph("Clock &mdash; a step that runs on a deadline; write the time beside it.", subp))
    s.append(Paragraph("Arrow &mdash; what happens next.", subp))
    s.append(Spacer(1, 8))
    s.append(Paragraph("<b>Remember:</b> role, not name &mdash; and every step needs its rule number. The next page shows a finished example.", body))
    s.append(PageBreak())
    return s

# ---------- generic drawing helpers ----------
def mk_box(d, H, x, w, yt, h, title, subtitle, rx=6):
    yb = H - (yt + h)
    d.add(Rect(x, yb, w, h, rx=rx, ry=rx, fillColor=white, strokeColor=black, strokeWidth=0.8))
    cx = x + w/2.0
    if subtitle:
        d.add(String(cx, yb + h/2 + 2.5, title, textAnchor='middle', fontName='Helvetica-Bold', fontSize=9.3, fillColor=black))
        d.add(String(cx, yb + h/2 - 9, subtitle, textAnchor='middle', fontName='Helvetica', fontSize=7.6, fillColor=black))
    else:
        d.add(String(cx, yb + h/2 - 3, title, textAnchor='middle', fontName='Helvetica-Bold', fontSize=9.3, fillColor=black))

def mk_pill(d, H, x, w, yt, h, title, fs=9.3):
    yb = H - (yt + h)
    d.add(Rect(x, yb, w, h, rx=h/2.0, ry=h/2.0, fillColor=white, strokeColor=black, strokeWidth=0.8))
    d.add(String(x + w/2.0, yb + h/2 - 3, title, textAnchor='middle', fontName='Helvetica-Bold', fontSize=fs, fillColor=black))

def mk_clock(d, H, cx, yt_center, r=5.5):
    cy = H - yt_center
    d.add(Circle(cx, cy, r, fillColor=white, strokeColor=black, strokeWidth=0.8))
    d.add(Line(cx, cy, cx, cy + r - 1.5, strokeColor=black, strokeWidth=0.8))
    d.add(Line(cx, cy, cx + r - 2, cy - 1, strokeColor=black, strokeWidth=0.8))

def mk_timerbox(d, H, x, w, yt, h, title, subtitle):
    mk_box(d, H, x, w, yt, h, title, subtitle)
    mk_clock(d, H, x + 13, yt + h/2.0)

def mk_diamond(d, H, cx, cy, label, hw=24, hh=22):
    y = H - cy
    d.add(Polygon([cx, y+hh, cx+hw, y, cx, y-hh, cx-hw, y], fillColor=white, strokeColor=black, strokeWidth=0.8))
    d.add(String(cx, y-3, label, textAnchor='middle', fontName='Helvetica-Bold', fontSize=8.2, fillColor=black))

def mk_arrow(d, H, x1, yt1, x2, yt2):
    p1 = (x1, H-yt1); p2 = (x2, H-yt2)
    d.add(Line(p1[0], p1[1], p2[0], p2[1], strokeColor=black, strokeWidth=0.9))
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]; L = math.hypot(dx,dy) or 1
    ux, uy = dx/L, dy/L; px, py = -uy, ux; a=8.0; wsp=3.0
    bx, by = p2[0]-ux*a, p2[1]-uy*a
    d.add(Polygon([p2[0], p2[1], bx+px*wsp, by+py*wsp, bx-px*wsp, by-py*wsp], fillColor=black, strokeColor=black, strokeWidth=0.3))

def mk_annot(d, H, x, yt_center, text, anchor='start'):
    d.add(String(x, H - yt_center - 2, text, textAnchor=anchor, fontName='Helvetica-Oblique', fontSize=7.4, fillColor=black))

def mk_axis(d, H, x, yt_top, yt_bottom, ticks):
    d.add(Line(x, H-yt_top, x, H-yt_bottom, strokeColor=black, strokeWidth=0.6))
    for cy, lab in ticks:
        d.add(Line(x-3, H-cy, x+3, H-cy, strokeColor=black, strokeWidth=0.8))
        d.add(String(x-7, H-cy-2.5, lab, textAnchor='end', fontName='Helvetica-Bold', fontSize=7.6, fillColor=black))

# ---------- diagram 1: redaction (no timeline) ----------
def draw_redaction():
    H = 490; d = Drawing(504, H)
    MX, MW = 120, 220; RX, RW = 352, 148
    mk_pill(d, H, MX, MW, 8, 26, "Request received")
    mk_arrow(d, H, 230, 34, 230, 54)
    mk_box(d, H, MX, MW, 54, 46, "Locate responsive records", f"Records custodian {EM} {SS}119.07(1)(a)")
    mk_arrow(d, H, 230, 100, 230, 120)
    mk_box(d, H, MX, MW, 120, 46, "Identify exempt content", f"Records custodian {EM} {SS}119.071")
    mk_arrow(d, H, 230, 166, 230, 178)
    mk_diamond(d, H, 230, 208, "Exempt?", hw=32, hh=30)
    mk_annot(d, H, 240, 250, "yes"); mk_arrow(d, H, 230, 238, 230, 258)
    mk_annot(d, H, 305, 201, "no"); mk_arrow(d, H, 286, 208, 352, 208)
    mk_box(d, H, MX, MW, 258, 46, "Apply redaction", f"Legal reviewer {EM} {SS}119.07(1)(d)")
    mk_arrow(d, H, 230, 304, 230, 324)
    mk_box(d, H, MX, MW, 324, 46, "State statutory basis", f"Legal reviewer {EM} {SS}119.07(1)(e)")
    mk_arrow(d, H, 230, 370, 230, 390)
    mk_box(d, H, MX, MW, 390, 46, "Release redacted record", "Records custodian")
    mk_arrow(d, H, 230, 436, 230, 456)
    mk_pill(d, H, MX, MW, 456, 26, "Record released")
    mk_box(d, H, RX, RW, 185, 46, "Release full record", f"Custodian {EM} {SS}119.07(1)")
    mk_arrow(d, H, 426, 231, 426, 251)
    mk_pill(d, H, RX, RW, 251, 26, "Record released")
    return d

# ---------- shared timeline layout ----------
CY = [30, 84, 138, 192, 246, 300, 354, 408, 462]
BH = 40; CENTER = 260; BX = 150; BW = 220; AXX = 70
SPX = 390; SPW = 110; SPH = 30

def yt(i):  # top of box for row i
    return CY[i] - BH/2.0

def spine_arrow(d, H, i, j):
    mk_arrow(d, H, CENTER, yt(i)+BH+2, CENTER, yt(j)-2)

# ---------- diagram 2: FOIA with timers ----------
def draw_foia():
    H = 496; d = Drawing(504, H)
    mk_axis(d, H, AXX, CY[0]-6, CY[8]+6,
            [(CY[0], "Day 0"), (CY[3], "by Day 20"), (CY[5], "within 90d"), (CY[7], "by Day 20")])
    mk_pill(d, H, BX, BW, yt(0), BH, "FOIA request submitted")
    spine_arrow(d, H, 0, 1)
    mk_box(d, H, BX, BW, yt(1), BH, "Acknowledge & log request", f"Agency {EM} {SS}552(a)(6)(A)")
    spine_arrow(d, H, 1, 2)
    mk_box(d, H, BX, BW, yt(2), BH, "Search & review for exemptions", f"Agency {EM} {SS}552(b)")
    spine_arrow(d, H, 2, 3)
    mk_timerbox(d, H, BX, BW, yt(3), BH, "Determination due", f"Agency {EM} {SS}552(a)(6)(A)(i)")
    mk_annot(d, H, SPX-6, CY[3]-6, "+10 days if unusual")
    mk_annot(d, H, SPX-6, CY[3]+6, f"circumstances {EM} {SS}552(a)(6)(B)")
    spine_arrow(d, H, 3, 4)
    mk_box(d, H, BX, BW, yt(4), BH, "Issue determination", f"grant {MID} partial {MID} deny")
    spine_arrow(d, H, 4, 5)
    mk_diamond(d, H, CENTER, CY[5], "Appeal?")
    mk_annot(d, H, CENTER+30, CY[5]-8, "no")
    mk_arrow(d, H, CENTER+24, CY[5], SPX, CY[5])
    mk_pill(d, H, SPX, SPW, CY[5]-SPH/2.0, SPH, "Request closed", fs=8.2)
    mk_arrow(d, H, CENTER, CY[5]+22+2, CENTER, yt(6)-2)
    mk_box(d, H, BX, BW, yt(6), BH, "File administrative appeal", f"Requester {EM} {SS}552(a)(6)(A)(ii)")
    spine_arrow(d, H, 6, 7)
    mk_timerbox(d, H, BX, BW, yt(7), BH, "Appeal decided", f"Agency {EM} {SS}552(a)(6)(A)(ii)")
    spine_arrow(d, H, 7, 8)
    mk_pill(d, H, BX, BW, yt(8), BH, "Judicial review available")
    mk_annot(d, H, SPX-6, CY[8], f"{SS}552(a)(4)(B)")
    return d

# ---------- diagram 3: Florida seal / expunge with timers ----------
def draw_seal():
    H = 496; d = Drawing(504, H)
    mk_axis(d, H, AXX, CY[0]-6, CY[8]+6,
            [(CY[0], "start"), (CY[2], "valid 12mo"), (CY[6], "on order")])
    mk_pill(d, H, BX, BW, yt(0), BH, "Application to FDLE")
    spine_arrow(d, H, 0, 1)
    mk_box(d, H, BX, BW, yt(1), BH, "FDLE determines eligibility", f"FDLE {EM} {SS}943.0585 / {SS}943.059")
    mk_annot(d, H, 380, CY[1]-8, "no", anchor='middle')
    mk_arrow(d, H, BX+BW, CY[1], SPX, CY[1])
    mk_pill(d, H, SPX, SPW, CY[1]-SPH/2.0, SPH, "Rejected", fs=8.2)
    spine_arrow(d, H, 1, 2)
    mk_timerbox(d, H, BX, BW, yt(2), BH, "Certificate of Eligibility issued", "FDLE")
    spine_arrow(d, H, 2, 3)
    mk_box(d, H, BX, BW, yt(3), BH, "File petition to seal / expunge", "Petitioner {} Rule 3.692".format(EM))
    mk_annot(d, H, SPX-6, CY[3], "before certificate expires")
    spine_arrow(d, H, 3, 4)
    mk_diamond(d, H, CENTER, CY[4], "Granted?")
    mk_annot(d, H, CENTER+30, CY[4]-8, "no")
    mk_annot(d, H, 150, CY[4]-4, "Court decides;")
    mk_annot(d, H, 150, CY[4]+7, "State may object")
    mk_arrow(d, H, CENTER+24, CY[4], SPX, CY[4])
    mk_pill(d, H, SPX, SPW, CY[4]-SPH/2.0, SPH, "Petition denied", fs=8.2)
    mk_arrow(d, H, CENTER, CY[4]+22+2, CENTER, yt(5)-2)
    mk_box(d, H, BX, BW, yt(5), BH, "Court enters seal / expunge order", "Court")
    spine_arrow(d, H, 5, 6)
    mk_timerbox(d, H, BX, BW, yt(6), BH, "Certified order to FDLE & agencies", "relief only on certified order")
    spine_arrow(d, H, 6, 7)
    mk_box(d, H, BX, BW, yt(7), BH, "Agencies seal / expunge record", "FDLE / criminal justice agencies")
    spine_arrow(d, H, 7, 8)
    mk_pill(d, H, BX, BW, yt(8), BH, "Removed from public criminal history", fs=8.6)
    return d

def build_packet(out, heading, intro, drawing, disclaimer):
    story = letter_and_guide()
    story.append(Paragraph(heading, head))
    story.append(Paragraph(intro, body))
    story.append(Spacer(1, 6))
    story.append(drawing)
    story.append(Spacer(1, 10))
    story.append(Paragraph(disclaimer, small))
    doc = SimpleDocTemplate(out, pagesize=letter, leftMargin=54, rightMargin=54,
                            topMargin=54, bottomMargin=54, title="Lexipedia Contributor Packet", author="Lexipedia")
    doc.build(story)
    print("built", out)

OUT = "/mnt/user-data/outputs/"
build_packet(OUT+"packet_1_redaction.pdf",
    "Worked example &mdash; public-records redaction",
    "A short process showing the style to copy. Notice how each box names the <b>role</b> that "
    "acts and cites the <b>rule</b> it comes from, and how the diamond splits into two arrows.",
    draw_redaction(),
    f"Not legal advice. Citations are to Florida&rsquo;s public-records law (Chapter 119, Florida Statutes) and are illustrative of the mapping style.")

build_packet(OUT+"packet_2_foia.pdf",
    "Worked example &mdash; a FOIA request, on the clock",
    "A federal Freedom of Information Act request. The times down the left are the statutory "
    "clock; a small <b>clock</b> marks a step that runs on a deadline. Each box still names the "
    "<b>role</b> and the <b>law</b>.",
    draw_foia(),
    f"Not legal advice. Citations are to the federal FOIA, 5 U.S.C. {SS}552. &ldquo;Business days&rdquo; exclude weekends and federal holidays.")

build_packet(OUT+"packet_3_seal.pdf",
    "Worked example &mdash; sealing or expunging a record",
    "How a Florida felony record is sealed or expunged so it drops off public background checks. "
    "Times down the left mark the deadlines; a <b>clock</b> marks a timed step; the first decision "
    "is an eligibility test (a natural fit for a decision table).",
    draw_seal(),
    f"Not legal advice. Citations are to Florida Statutes {SS}{SS}943.0585 and 943.059 and Fla. R. Crim. P. 3.692. A Certificate of Eligibility does not guarantee a court will grant relief.")
