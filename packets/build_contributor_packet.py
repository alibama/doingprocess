import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.colors import black, white
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.graphics.shapes import Drawing, Rect, Line, String, Polygon, Circle

EM = "\u2014"; SS = "\u00a7"; MID = "\u00b7"
styles = getSampleStyleSheet()
body = ParagraphStyle('body', parent=styles['Normal'], fontName='Helvetica', fontSize=10.5, leading=14.5, spaceAfter=8, alignment=TA_LEFT)
subp = ParagraphStyle('subp', parent=body, leftIndent=14, spaceAfter=4)
head = ParagraphStyle('head', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=16, spaceAfter=10)
kicker = ParagraphStyle('kicker', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8.5, leading=11, spaceAfter=14)
quote = ParagraphStyle('quote', parent=body, fontName='Helvetica-Oblique', leftIndent=18, rightIndent=18, spaceBefore=4, spaceAfter=10)
small = ParagraphStyle('small', parent=body, fontSize=9, leading=12.5, spaceAfter=6)

# ---------- helpers (shared with the timeline packets) ----------
def T(H, yt): return H - yt
def mk_box(d,H,x,w,yt,h,title,subtitle,rx=6):
    yb=H-(yt+h); d.add(Rect(x,yb,w,h,rx=rx,ry=rx,fillColor=white,strokeColor=black,strokeWidth=0.8)); cx=x+w/2.0
    if subtitle:
        d.add(String(cx,yb+h/2+2.5,title,textAnchor='middle',fontName='Helvetica-Bold',fontSize=9.3,fillColor=black))
        d.add(String(cx,yb+h/2-9,subtitle,textAnchor='middle',fontName='Helvetica',fontSize=7.6,fillColor=black))
    else:
        d.add(String(cx,yb+h/2-3,title,textAnchor='middle',fontName='Helvetica-Bold',fontSize=9.3,fillColor=black))
def mk_pill(d,H,x,w,yt,h,title,fs=9.3):
    yb=H-(yt+h); d.add(Rect(x,yb,w,h,rx=h/2.0,ry=h/2.0,fillColor=white,strokeColor=black,strokeWidth=0.8))
    d.add(String(x+w/2.0,yb+h/2-3,title,textAnchor='middle',fontName='Helvetica-Bold',fontSize=fs,fillColor=black))
def mk_clock(d,H,cx,yt_center,r=5.5):
    cy=H-yt_center; d.add(Circle(cx,cy,r,fillColor=white,strokeColor=black,strokeWidth=0.8))
    d.add(Line(cx,cy,cx,cy+r-1.5,strokeColor=black,strokeWidth=0.8)); d.add(Line(cx,cy,cx+r-2,cy-1,strokeColor=black,strokeWidth=0.8))
def mk_timerbox(d,H,x,w,yt,h,title,subtitle):
    mk_box(d,H,x,w,yt,h,title,subtitle); mk_clock(d,H,x+13,yt+h/2.0)
def mk_diamond(d,H,cx,cy,label,hw=24,hh=22):
    y=H-cy; d.add(Polygon([cx,y+hh,cx+hw,y,cx,y-hh,cx-hw,y],fillColor=white,strokeColor=black,strokeWidth=0.8))
    d.add(String(cx,y-3,label,textAnchor='middle',fontName='Helvetica-Bold',fontSize=8.2,fillColor=black))
def mk_arrow(d,H,x1,yt1,x2,yt2,dash=None):
    p1=(x1,H-yt1); p2=(x2,H-yt2); ln=Line(p1[0],p1[1],p2[0],p2[1],strokeColor=black,strokeWidth=0.9)
    if dash: ln.strokeDashArray=dash
    d.add(ln)
    dx,dy=p2[0]-p1[0],p2[1]-p1[1]; L=math.hypot(dx,dy) or 1; ux,uy=dx/L,dy/L; px,py=-uy,ux; a=8.0; wsp=3.0
    bx,by=p2[0]-ux*a,p2[1]-uy*a
    d.add(Polygon([p2[0],p2[1],bx+px*wsp,by+py*wsp,bx-px*wsp,by-py*wsp],fillColor=black,strokeColor=black,strokeWidth=0.3))
def mk_annot(d,H,x,yt_center,text,anchor='start'):
    d.add(String(x,H-yt_center-2,text,textAnchor=anchor,fontName='Helvetica-Oblique',fontSize=7.4,fillColor=black))
def mk_axis(d,H,x,yt_top,yt_bottom,ticks):
    d.add(Line(x,H-yt_top,x,H-yt_bottom,strokeColor=black,strokeWidth=0.6))
    for cy,lab in ticks:
        d.add(Line(x-3,H-cy,x+3,H-cy,strokeColor=black,strokeWidth=0.8))
        d.add(String(x-7,H-cy-2.5,lab,textAnchor='end',fontName='Helvetica-Bold',fontSize=7.6,fillColor=black))

CY=[30,84,138,192,246,300,354,408,462]; BH=40; CENTER=260; BX=150; BW=220; AXX=70; SPX=390; SPW=110; SPH=30
def yt(i): return CY[i]-BH/2.0
def spine(d,H,i,j): mk_arrow(d,H,CENTER,yt(i)+BH+2,CENTER,yt(j)-2)

def draw_foia():
    H=496; d=Drawing(504,H)
    mk_axis(d,H,AXX,CY[0]-6,CY[8]+6,[(CY[0],"Day 0"),(CY[3],"by Day 20"),(CY[5],"within 90d"),(CY[7],"by Day 20")])
    mk_pill(d,H,BX,BW,yt(0),BH,"FOIA request submitted"); spine(d,H,0,1)
    mk_box(d,H,BX,BW,yt(1),BH,"Acknowledge & log request",f"Agency {EM} {SS}552(a)(6)(A)"); spine(d,H,1,2)
    mk_box(d,H,BX,BW,yt(2),BH,"Search & review for exemptions",f"Agency {EM} {SS}552(b)"); spine(d,H,2,3)
    mk_timerbox(d,H,BX,BW,yt(3),BH,"Determination due",f"Agency {EM} {SS}552(a)(6)(A)(i)")
    mk_annot(d,H,SPX-6,CY[3]-6,"+10 days if unusual"); mk_annot(d,H,SPX-6,CY[3]+6,f"circumstances {EM} {SS}552(a)(6)(B)"); spine(d,H,3,4)
    mk_box(d,H,BX,BW,yt(4),BH,"Issue determination",f"grant {MID} partial {MID} deny"); spine(d,H,4,5)
    mk_diamond(d,H,CENTER,CY[5],"Appeal?"); mk_annot(d,H,CENTER+30,CY[5]-8,"no")
    mk_arrow(d,H,CENTER+24,CY[5],SPX,CY[5]); mk_pill(d,H,SPX,SPW,CY[5]-SPH/2.0,SPH,"Request closed",fs=8.2)
    mk_arrow(d,H,CENTER,CY[5]+22+2,CENTER,yt(6)-2)
    mk_box(d,H,BX,BW,yt(6),BH,"File administrative appeal",f"Requester {EM} {SS}552(a)(6)(A)(ii)"); spine(d,H,6,7)
    mk_timerbox(d,H,BX,BW,yt(7),BH,"Appeal decided",f"Agency {EM} {SS}552(a)(6)(A)(ii)"); spine(d,H,7,8)
    mk_pill(d,H,BX,BW,yt(8),BH,"Judicial review available"); mk_annot(d,H,SPX-6,CY[8],f"{SS}552(a)(4)(B)")
    return d

# ---------- NEW: BPMN glyph + scan cheat-sheet ----------
def ev(d,H,cx,cyt,double=False,bold=False):
    cy=H-cyt
    if double: d.add(Circle(cx,cy,11,fillColor=white,strokeColor=black,strokeWidth=0.8))
    d.add(Circle(cx,cy,(11 if not double else 8),fillColor=white,strokeColor=black,strokeWidth=(2.4 if bold else 0.9)))
def envelope(d,H,cx,cyt):
    cy=H-cyt; d.add(Rect(cx-6,cy-3.5,12,7,fillColor=white,strokeColor=black,strokeWidth=0.7))
    d.add(Polygon([cx-6,cy+3.5,cx,cy-0.5,cx+6,cy+3.5],fillColor=None,strokeColor=black,strokeWidth=0.7))
def clockg(d,H,cx,cyt):
    cy=H-cyt; d.add(Circle(cx,cy,6,fillColor=None,strokeColor=black,strokeWidth=0.8))
    d.add(Line(cx,cy,cx,cy+4,strokeColor=black,strokeWidth=0.8)); d.add(Line(cx,cy,cx+3,cy,strokeColor=black,strokeWidth=0.8))
def lbl(d,H,x,cyt,text,bold=False,fs=8.6):
    d.add(String(x,H-cyt-3,text,textAnchor='start',fontName=('Helvetica-Bold' if bold else 'Helvetica'),fontSize=fs,fillColor=black))
def diamondg(d,H,cx,cyt,kind):
    cy=H-cyt; hw=hh=12; d.add(Polygon([cx,cy+hh,cx+hw,cy,cx,cy-hh,cx-hw,cy],fillColor=white,strokeColor=black,strokeWidth=0.9))
    if kind=='x':
        d.add(Line(cx-5,cy-5,cx+5,cy+5,strokeColor=black,strokeWidth=1.2)); d.add(Line(cx-5,cy+5,cx+5,cy-5,strokeColor=black,strokeWidth=1.2))
    else:
        d.add(Line(cx-6,cy,cx+6,cy,strokeColor=black,strokeWidth=1.2)); d.add(Line(cx,cy-6,cx,cy+6,strokeColor=black,strokeWidth=1.2))

def draw_cheatsheet():
    H=372; d=Drawing(504,H)
    # left column glyphs
    ax=48; alx=70
    rowsL=[25,70,115,160,205]
    ev(d,H,ax,rowsL[0]); lbl(d,H,alx,rowsL[0],"Start",bold=True); lbl(d,H,alx+42,rowsL[0],"thin circle (process begins)")
    ev(d,H,ax,rowsL[1],bold=True); lbl(d,H,alx,rowsL[1],"End",bold=True); lbl(d,H,alx+38,rowsL[1],"bold circle (process ends)")
    ev(d,H,ax,rowsL[2],double=True); clockg(d,H,ax,rowsL[2]); lbl(d,H,alx,rowsL[2],"Timer",bold=True); lbl(d,H,alx+48,rowsL[2],"clock: a deadline/wait")
    ev(d,H,ax,rowsL[3],double=True); envelope(d,H,ax,rowsL[3]); lbl(d,H,alx,rowsL[3],"Message",bold=True); lbl(d,H,alx+66,rowsL[3],"envelope: a notice/filing")
    # data object (page w/ folded corner)
    cy=H-rowsL[4]; d.add(Polygon([ax-8,cy-11,ax+5,cy-11,ax+8,cy-6,ax+8,cy+11,ax-8,cy+11],fillColor=white,strokeColor=black,strokeWidth=0.8))
    d.add(Polygon([ax+5,cy-11,ax+5,cy-6,ax+8,cy-6],fillColor=None,strokeColor=black,strokeWidth=0.8))
    lbl(d,H,alx,rowsL[4],"Document",bold=True); lbl(d,H,alx+58,rowsL[4],"a form / record")
    # right column glyphs
    bx=290; blx=312; rowsR=[25,70,115,160,205]
    d.add(Rect(bx-16,H-rowsR[0]-11,32,22,rx=5,ry=5,fillColor=white,strokeColor=black,strokeWidth=0.9)); lbl(d,H,blx,rowsR[0],"Task",bold=True); lbl(d,H,blx+34,rowsR[0],"a step someone does")
    d.add(Rect(bx-16,H-rowsR[1]-11,32,22,rx=5,ry=5,fillColor=white,strokeColor=black,strokeWidth=0.9))
    d.add(Line(bx-3,H-rowsR[1]-9,bx+3,H-rowsR[1]-9,strokeColor=black,strokeWidth=1)); d.add(Line(bx,H-rowsR[1]-12,bx,H-rowsR[1]-6,strokeColor=black,strokeWidth=1))
    lbl(d,H,blx,rowsR[1],"Sub-process",bold=True); lbl(d,H,blx+68,rowsR[1],"box with a +")
    diamondg(d,H,bx,rowsR[2],'x'); lbl(d,H,blx,rowsR[2],"Either/or",bold=True); lbl(d,H,blx+52,rowsR[2],"X: one path is taken")
    diamondg(d,H,bx,rowsR[3],'+'); lbl(d,H,blx,rowsR[3],"Both",bold=True); lbl(d,H,blx+34,rowsR[3],"+: paths run together")
    # pool
    d.add(Rect(bx-16,H-rowsR[4]-11,120,22,fillColor=white,strokeColor=black,strokeWidth=0.8)); d.add(Line(bx-4,H-rowsR[4]-11,bx-4,H-rowsR[4]+11,strokeColor=black,strokeWidth=0.8))
    lbl(d,H,blx+92,rowsR[4],"Pool",bold=True); lbl(d,H,blx+92,rowsR[4]+11,"= one party")
    # edges band
    ex1,ex2=40,120; erows=[250,285,320]
    mk_arrow(d,H,ex1,erows[0],ex2,erows[0]); lbl(d,H,135,erows[0],"Solid arrow",bold=True); lbl(d,H,205,erows[0],"= the next step (sequence)")
    mk_arrow(d,H,ex1,erows[1],ex2,erows[1],dash=[4,3]); lbl(d,H,135,erows[1],"Dashed arrow",bold=True); lbl(d,H,215,erows[1],"= a message between parties")
    mk_arrow(d,H,ex1,erows[2],ex2,erows[2],dash=[1,3]); lbl(d,H,135,erows[2],"Dotted arrow",bold=True); lbl(d,H,205,erows[2],"= to / from a document")
    return d

def letter_and_guide():
    s=[Paragraph("LEXIPEDIA &mdash; CONTRIBUTOR INVITATION", kicker),
       Paragraph("Dear contributor,", body),
       Paragraph("Thank you for your interest in Lexipedia. Lexipedia is a free, public encyclopedia of legal <i>processes</i> &mdash; not legal advice, but plain maps of how a legal procedure works: who does what, in what order, and under which law. Everything in it is open and free for anyone to read.", body),
       Paragraph("You know legal processes that most people never see up close &mdash; grievances, disciplinary hearings, appeals, records requests, parole steps. Mapping one is a real contribution, and this letter explains how to do it entirely by mail. You do not need a computer or internet.", body),
       Paragraph("<b>How it works.</b> You draw a process on paper and mail it to me. I scan it, a tool reads your drawing into a digital map, I check it, and it is added to the public collection, where it may be combined and cross-referenced with other maps. The page you sent is kept on file.", body),
       Paragraph("Drawing a map is explained on the next page, with a shapes key and a worked example. Two things matter most:", body),
       Paragraph("&mdash; Write each step as an action, and name the <b>role</b> that does it &mdash; never a specific person&rsquo;s name.", subp),
       Paragraph("&mdash; Write the law or rule number next to each step. A step without its citation cannot be used, so this is the single most important field.", subp),
       Paragraph("<b>Your name and credit.</b> You are never published under your legal name. Pick a handle (any pen name) and write it on your map. When I write back, I will send you a short contributor number &mdash; please put that number on everything you send afterward, so your maps stay linked to you for credit and for our records. If you would rather show no public name at all, just write &ldquo;no public credit&rdquo;; your work still counts and is still tracked by your number. (The mailroom requires your committed name and DOC number on the envelope; I remove those before anything is published.)", body),
       Paragraph("<b>Permission to publish.</b> Because everything here is free and open, I need your okay. If you agree, copy this line onto your map in your own hand and sign with your handle:", body),
       Paragraph("&ldquo;I agree my contributions may be published in Lexipedia and placed in the public domain (CC0), under my handle or with no public credit, as I choose.&rdquo;", quote),
       Paragraph("<b>A few practical notes.</b> This is a volunteer, educational project &mdash; there is no payment. Keep maps to plain legal procedure (boxes, arrows, rule numbers). Please do not include anything about weapons, drugs, escape, or facility security &mdash; mailroom rules will reject it. Keep it to a few standard-size pages, nothing stapled or taped.", body),
       Paragraph("If you have questions, write back. Thank you for helping make the law more legible to everyone.", body),
       Spacer(1,10), Paragraph("&mdash; [Your name]", body), Paragraph("Lexipedia &middot; [return address]", small), PageBreak()]
    # guide
    s+=[Paragraph("How to draw a process map", head),
        Paragraph("Use one page per process. At the top, write the process name and the system it belongs to (for example: &ldquo;Florida inmate grievance &mdash; FDC&rdquo;). Then:", body)]
    steps=["Draw a box for each step. Write the step as an action: &ldquo;File informal grievance,&rdquo; &ldquo;Warden responds,&rdquo; &ldquo;Appeal to the Secretary.&rdquo;",
           "Next to each box, write the <b>role</b> that does it &mdash; inmate, warden, grievance coordinator &mdash; not a person&rsquo;s name.",
           "Next to each box, write the law or rule it comes from (a statute or rule number, e.g. a Florida Administrative Code rule such as 33-103). This is required.",
           "Use a diamond for a yes/no decision, with an arrow leaving each answer.",
           "If a step has a deadline, write the time next to it (&ldquo;within 15 days&rdquo;) and a small clock.",
           "Draw a single circle where the process starts and a doubled circle where it ends.",
           "At the bottom, list the rulebooks or statutes you used."]
    for i,t in enumerate(steps,1): s.append(Paragraph(f"{i}.&nbsp;&nbsp;{t}", subp))
    s+=[Spacer(1,6),
        Paragraph("So a machine can read your drawing too, the next page shows the standard shapes and a few habits that keep your scan clean. The clearer the drawing, the fewer changes anyone has to make before it joins the collection.", body),
        PageBreak()]
    return s

def build():
    story=letter_and_guide()
    # page 3: cheat sheet
    story.append(Paragraph("Draw so we can read it", head))
    story.append(Paragraph("Copy these standard shapes. A scanner reads a clean, closed drawing far better than a rushed one &mdash; and the closer your drawing is to these, the less anyone has to change.", body))
    story.append(Spacer(1,4)); story.append(draw_cheatsheet()); story.append(Spacer(1,6))
    tips=["Use a dark pen, not pencil. Plain or lightly-lined paper reads best; heavy graph paper adds lines that confuse the scan.",
          "Write on one side of the page only, so nothing shows through from the back.",
          "Keep your drawing clear of hole-punches and away from the very edge of the page.",
          "Close every shape, and make each arrow actually touch the boxes it joins.",
          "Print your letters, keep each label&rsquo;s words together, and write straight across (not slanted).",
          "To fix a mistake, cross it out with one clean line and redraw &mdash; please don&rsquo;t scribble over it.",
          "Scan or photograph the whole page flat, straight, and in good light."]
    for t in tips: story.append(Paragraph("&mdash;&nbsp;&nbsp;"+t, subp))
    story.append(PageBreak())
    # page 4: worked example
    story.append(Paragraph("Worked example &mdash; a FOIA request, on the clock", head))
    story.append(Paragraph("A federal Freedom of Information Act request. The times down the left are the statutory clock; a small <b>clock</b> marks a step that runs on a deadline. Each box names the <b>role</b> and the <b>law</b> &mdash; drawn in the standard shapes from the previous page.", body))
    story.append(Spacer(1,6)); story.append(draw_foia()); story.append(Spacer(1,10))
    story.append(Paragraph(f"Not legal advice. Citations are to the federal FOIA, 5 U.S.C. {SS}552. &ldquo;Business days&rdquo; exclude weekends and federal holidays.", small))
    out="/mnt/user-data/outputs/packet_foia_recognizable.pdf"
    SimpleDocTemplate(out,pagesize=letter,leftMargin=54,rightMargin=54,topMargin=54,bottomMargin=54,
                      title="Lexipedia Contributor Packet (FOIA, recognizable)",author="Lexipedia").build(story)
    print("built",out)

build()
