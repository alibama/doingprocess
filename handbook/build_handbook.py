import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import HexColor, white
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                Table, TableStyle, ListFlowable, ListItem)
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon, Circle

INK=HexColor("#1b1813"); TEAL=HexColor("#0d6b60"); OCHRE=HexColor("#b0741a")
SOFT=HexColor("#514c41"); LINE=HexColor("#cec8b8"); PAPER=HexColor("#f1eee6")
SS="\u00a7"; EM="\u2014"; MID="\u00b7"

styles=getSampleStyleSheet()
H1=ParagraphStyle('H1',parent=styles['Normal'],fontName='Times-Bold',fontSize=22,leading=25,textColor=INK,spaceAfter=6)
H2=ParagraphStyle('H2',parent=styles['Normal'],fontName='Times-Bold',fontSize=14.5,leading=18,textColor=INK,spaceBefore=14,spaceAfter=6)
EYE=ParagraphStyle('EYE',parent=styles['Normal'],fontName='Courier-Bold',fontSize=8,leading=11,textColor=TEAL,spaceAfter=3)
BODY=ParagraphStyle('BODY',parent=styles['Normal'],fontName='Times-Roman',fontSize=10.5,leading=15,textColor=INK,spaceAfter=8,alignment=TA_LEFT)
LI=ParagraphStyle('LI',parent=BODY,spaceAfter=3)
CAP=ParagraphStyle('CAP',parent=BODY,fontName='Courier',fontSize=8,leading=11,textColor=SOFT,spaceAfter=6)
LEAD=ParagraphStyle('LEAD',parent=BODY,fontSize=12,leading=17,textColor=SOFT,spaceAfter=10)

def bullets(items,style=LI):
    return ListFlowable([ListItem(Paragraph(t,style),leftIndent=10,value='\u2013') for t in items],
                        bulletType='bullet',start='\u2013',leftIndent=12)

story=[]
# ---- cover ----
story.append(Spacer(1,60))
story.append(Paragraph("DOINGPROCESS.ORG",EYE))
story.append(Paragraph("Doing Process",H1))
story.append(Paragraph("A handbook",ParagraphStyle('sub',parent=H1,fontName='Times-Italic',fontSize=16,textColor=SOFT,spaceAfter=18)))
story.append(Paragraph("Turning hand-drawn maps of legal processes — many of them drawn by people inside prisons — "
    "into a public, machine-readable encyclopedia of how the law actually works.",LEAD))
story.append(Spacer(1,10))
story.append(Paragraph("Doing process is due process.",ParagraphStyle('tag',parent=BODY,fontName='Times-Italic',fontSize=13,textColor=TEAL)))
story.append(Spacer(1,30))
story.append(Paragraph("Code: Apache-2.0 &nbsp;&middot;&nbsp; Contributed maps: CC0-1.0 &nbsp;&middot;&nbsp; Runs entirely on your own hardware",CAP))
story.append(PageBreak())

# ---- 1 the idea ----
story.append(Paragraph("PART ONE",EYE))
story.append(Paragraph("The idea",H1))
story.append(Paragraph("A legal process is a sequence of steps: who does what, in what order, and under which law. "
    "People navigating the system up close &mdash; filing grievances, appealing, seeking parole, trying to seal a "
    "record &mdash; often understand these processes better than anyone. That knowledge is usually invisible and "
    "uncredited.",BODY))
story.append(Paragraph("Doing Process captures it as a <b>process map</b> in BPMN, a standard notation of boxes, "
    "arrows, and decision diamonds. A map drawn on paper can be scanned, read by software into a machine-readable "
    "model, checked, and published &mdash; free for anyone to read, forever.",BODY))
story.append(Paragraph("Why maps, not prose",H2))
story.append(bullets([
    "<b>They compose.</b> Maps merge and cross-reference; a step in one becomes a link in another.",
    "<b>They&rsquo;re checkable.</b> Every step must cite the law it comes from, so gaps and errors are visible.",
    "<b>They&rsquo;re executable.</b> The same model that teaches a person can drive a workflow tool.",
    "<b>They credit the author.</b> Contributions are tracked under a chosen handle, across every map.",
]))

# ---- 2 the path (drawn as a numbered process) ----
story.append(Paragraph("PART TWO",EYE))
story.append(Paragraph("From a mailed drawing to the commons",H1))
story.append(Paragraph("The path a single map travels. It is itself a process &mdash; so here it is as one.",CAP))

def pipeline_drawing():
    W,H=516,150; d=Drawing(W,H)
    steps=[("1","Draw","on paper"),("2","Mail & scan","intake"),("3","Recognize","sketch \u2192 BPMN"),
           ("4","Check","lint the law"),("5","Sign off","human + CC0"),("6","Publish","into Lexipedia")]
    n=len(steps); bw=68; bh=44; gap=(W-2-n*bw)/(n-1); y=70
    d.add(Circle(0,H-y-bh/2+bh/2,0)) # noop
    # start dot
    cx0=-6
    for i,(num,title,cap) in enumerate(steps):
        x=1+i*(bw+gap); yb=H-(y+bh)
        d.add(Rect(x,yb,bw,bh,rx=6,ry=6,fillColor=PAPER,strokeColor=TEAL,strokeWidth=1))
        d.add(String(x+8,yb+bh-13,num,fontName='Courier-Bold',fontSize=9,fillColor=OCHRE))
        d.add(String(x+bw/2,yb+bh/2-1,title,textAnchor='middle',fontName='Times-Bold',fontSize=8.6,fillColor=INK))
        d.add(String(x+bw/2,yb+11,cap,textAnchor='middle',fontName='Courier',fontSize=6.2,fillColor=SOFT))
        if i<n-1:
            ax=x+bw+2; ay=H-(y+bh/2)
            d.add(Line(ax,ay,ax+gap-4,ay,strokeColor=INK,strokeWidth=0.8))
            d.add(Polygon([ax+gap-4,ay,ax+gap-9,ay+3,ax+gap-9,ay-3],fillColor=INK,strokeColor=INK))
    return d
story.append(pipeline_drawing())
story.append(Spacer(1,4))
for num,txt in [
 ("1","<b>Draw.</b> One process per page: a box for each step (an action), the <b>role</b> that does it, and the "
      "law or rule number beside it. A diamond for a yes/no decision; a clock for a deadline."),
 ("2","<b>Mail &amp; scan.</b> The page is mailed in, scanned, and conditioned (deskewed, cleaned) so software can read it."),
 ("3","<b>Recognize.</b> A local model turns the drawing into a BPMN model. A purpose-built detector reads the shapes "
      "as drawn; a local vision model is the fallback. Nothing is sent to a cloud service."),
 ("4","<b>Check.</b> An automatic linter enforces the house rules &mdash; every timed step has a real deadline, every "
      "step cites its authority, nothing unsupported slips into an executable model."),
 ("5","<b>Sign off.</b> A person reviews and corrects the map, strips identifying details, and releases it under CC0 "
      "with the contributor&rsquo;s chosen handle (or no public name). No map publishes without this step."),
 ("6","<b>Publish.</b> The map enters Lexipedia, where it is merged and cross-referenced with the rest of the corpus."),
]:
    story.append(Paragraph(txt,LI))
story.append(PageBreak())

# ---- 3 contributor handbook ----
story.append(Paragraph("PART THREE",EYE))
story.append(Paragraph("For contributors",H1))
story.append(Paragraph("How to draw a map we can read",H2))
story.append(bullets([
    "Use one page per process. At the top, write the process name and the system (e.g. &ldquo;Florida inmate grievance &mdash; FDC&rdquo;).",
    "Write each step as an action; name the <b>role</b> that does it &mdash; never a specific person.",
    "Write the law or rule number next to each step. A step without its citation can&rsquo;t be used.",
    "Diamond = a yes/no decision. Clock = a deadline (write the time). Circle = start; doubled circle = end.",
    "Use a dark pen on plain paper; keep arrows touching the boxes they join; write labels straight across.",
]))
story.append(Paragraph("Your name, your terms",H2))
story.append(Paragraph("You are never published under your legal name. You pick a handle, and choose whether it&rsquo;s "
    "shown publicly at all &mdash; your work is tracked either way so credit and contribution history follow you. By "
    "contributing you agree your maps may be published in the public domain (CC0). The identity model has three layers:",BODY))
story.append(bullets([
    "<b>Legal identity</b> (name, DOC number) &mdash; used only to handle the mail; removed before anything is published.",
    "<b>Contributor ID</b> &mdash; a stable, private key that links your maps for credit and analytics.",
    "<b>Handle</b> &mdash; an optional public pen name; leave it off for no public credit.",
]))

# ---- 4 operator handbook ----
story.append(Paragraph("PART FOUR",EYE))
story.append(Paragraph("For operators",H1))
story.append(Paragraph("Running the intake is a short, auditable pipeline. Every stage is local; a human signs off "
    "before the corpus is touched.",BODY))
story.append(bullets([
    "<b>Redaction first.</b> Treat the scanned originals as sensitive. Strip legal identity before publishing; keep the linkage only in the restricted archive.",
    "<b>Recognize locally.</b> Detector track (renders as drawn) or local vision model. OCR runs locally or is skipped &mdash; no cloud.",
    "<b>Lint before merge.</b> Timers carry ISO-8601 durations; timed steps cite authority; business rules reference a decision; nothing outside the executable set reaches an executable copy.",
    "<b>Provenance + sign-off.</b> Each map ships with a record: source hash, contributor ID, license, reviewer. Promotion is blocked on errors.",
]))
story.append(Paragraph("The commons",H2))
story.append(Paragraph("Code is Apache-2.0; contributed maps are CC0. The whole pipeline runs on owned hardware with "
    "local models &mdash; a deliberate choice so contributor material never depends on a third party. Built on open "
    "standards and projects: BPMN &amp; DMN, SpiffWorkflow, bpmn-js, and the hdBPMN hand-drawn dataset.",BODY))

# ---- 5 value ----
story.append(Paragraph("PART FIVE",EYE))
story.append(Paragraph("Where it&rsquo;s of value",H1))
data=[
 ["For people in the system","Plain, followable maps for grievances, appeals, record sealing/expungement, and records requests &mdash; for pro se litigants and people reentering."],
 ["For legal aid & clinics","A shared, citable library of procedure that a clinic can hand a client or build intake around."],
 ["For researchers","A growing corpus for process mining and conformance work &mdash; how procedures are written versus how they run."],
 ["For courts & civic tech","Process made legible: the same map explains a procedure to a person and drives a workflow tool."],
 ["For contributors","Recognition for hard-won procedural knowledge, a durable record of authorship, and a public good built from it."],
]
t=Table([[Paragraph("<b>"+a+"</b>",BODY),Paragraph(b,BODY)] for a,b in data],colWidths=[135,350])
t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,-2),0.4,LINE),
    ('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7),('LEFTPADDING',(0,0),(0,-1),0)]))
story.append(t)
story.append(Spacer(1,16))
story.append(Paragraph("doingprocess.org",EYE))
story.append(Paragraph("Not legal advice. Doing Process publishes maps of how legal processes work; it does not "
    "provide legal representation or advice.",CAP))

SimpleDocTemplate("/mnt/user-data/outputs/doingprocess-handbook.pdf",pagesize=letter,
    leftMargin=64,rightMargin=64,topMargin=58,bottomMargin=54,title="Doing Process — Handbook",
    author="doingprocess.org").build(story)
print("handbook built")
