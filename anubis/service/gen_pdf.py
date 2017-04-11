import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

from anubis.util import options

options.define('ttf_font_name', 'fzyh.ttf', 'Name of TTF Font')

A4_TRANSVERSE = A4[::-1]
pdfmetrics.registerFont(TTFont('my_font', options.options.ttf_font_name))


def gen_team_pdf(team_tuples: list, fontsize: int=72):
    buf = io.BytesIO()
    canv = canvas.Canvas(buf, pagesize=A4_TRANSVERSE)
    style = ParagraphStyle(name='default', fontName='my_font', fontSize=fontsize,
                           alignment=1, leading=fontsize * 1.2)
    for index, team in team_tuples:
        paragraph = Paragraph('Team {0}<br />{1}'.format(index, team['team_name']), style)
        w, h = paragraph.wrap(A4_TRANSVERSE[0] - 100, A4_TRANSVERSE[1] - 100)
        paragraph.drawOn(canv, (A4_TRANSVERSE[0] - w) / 2, (A4_TRANSVERSE[1] - h) / 2)
        canv.showPage()

    canv.save()
    return buf.getvalue()
