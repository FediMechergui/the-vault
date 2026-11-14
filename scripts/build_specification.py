"""Build THE VAULT's revised French specification from its editable JSON source.

Install docs/requirements.txt in a separate environment; see docs/specification/README.md.
Each source page must fit its frame: overflow fails the build instead of hiding text.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable, Frame, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[1]
PAGE_W, PAGE_H = A4
MARGIN = 41
WIDTH = PAGE_W - 2 * MARGIN
INK = colors.HexColor('#172021')
MUTED = colors.HexColor('#52605f')
LIME = colors.HexColor('#d4ef78')
PALE = colors.HexColor('#f0f4ec')
LINE = colors.HexColor('#d8dfd9')


def fonts():
    folder = ROOT / 'docs/fonts'
    for name, filename in [('Vault', 'DejaVuSans.ttf'), ('VaultBold', 'DejaVuSans-Bold.ttf'),
                           ('VaultItalic', 'DejaVuSans-Oblique.ttf')]:
        pdfmetrics.registerFont(TTFont(name, str(folder / filename)))
    pdfmetrics.registerFontFamily('Vault', normal='Vault', bold='VaultBold',
                                 italic='VaultItalic', boldItalic='VaultBold')


def styles():
    body = ParagraphStyle('body', fontName='Vault', fontSize=9.5, leading=14,
                          textColor=INK, spaceAfter=9, alignment=TA_LEFT)
    return {
        'body': body,
        'small': ParagraphStyle('small', parent=body, fontSize=8.3, leading=12, spaceAfter=0),
        'cell': ParagraphStyle('cell', parent=body, fontSize=8.6, leading=12.5, spaceAfter=0),
        'headcell': ParagraphStyle('headcell', parent=body, fontName='VaultBold', fontSize=8.5,
                                   leading=12, textColor=colors.white, spaceAfter=0),
        'h': ParagraphStyle('heading', parent=body, fontName='VaultBold', fontSize=12,
                           leading=17, spaceBefore=5, spaceAfter=7),
        'code': ParagraphStyle('code', parent=body, fontName='Courier', fontSize=8.3,
                              leading=12, spaceAfter=0, splitLongWords=True),
        'toc': ParagraphStyle('toc', parent=body, fontSize=9, leading=13, spaceAfter=0),
        'bullet': ParagraphStyle('bullet', parent=body, leftIndent=11, firstLineIndent=-11,
                                spaceAfter=5),
    }


def paragraph(text, style, markup=False):
    return Paragraph(text if markup else escape(text).replace('\n', '<br/>'), style)


def box(text, style, background=PALE, title=None):
    body = ([paragraph(title, style['h'])] if title else []) + [paragraph(text, style['small'])]
    table = Table([[body]], colWidths=[WIDTH])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), background),
        ('BOX', (0, 0), (-1, -1), .5, LINE),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 10),
    ]))
    return table


class Architecture(Flowable):
    """Vector diagram of the verified local deployment (no raster assets needed)."""
    def __init__(self):
        super().__init__()
        self.width, self.height = WIDTH, 280

    def draw(self):
        c = self.canv

        def node(x, y, w, h, title, lines, fill=PALE):
            c.setFillColor(fill)
            c.setStrokeColor(LINE)
            c.roundRect(x, y, w, h, 6, fill=1, stroke=1)
            c.setFillColor(INK)
            c.setFont('VaultBold', 10)
            c.drawString(x + 12, y + h - 20, title)
            c.setFont('Vault', 8)
            for i, line in enumerate(lines):
                c.drawString(x + 12, y + h - 36 - i * 12, line)

        def arrow(x1, y1, x2, y2):
            import math
            c.setStrokeColor(MUTED)
            c.setLineWidth(1)
            c.line(x1, y1, x2, y2)
            angle = math.atan2(y2 - y1, x2 - x1)
            for delta in (-.45, .45):
                c.line(x2, y2, x2 - 6 * math.cos(angle + delta),
                       y2 - 6 * math.sin(angle + delta))

        c.setFillColor(colors.HexColor('#f8faf6'))
        c.roundRect(173, 10, WIDTH - 173, 259, 8, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont('VaultBold', 8)
        c.drawString(188, 251, 'PC PERSONNEL / COMPTE OS ACTIVÉ')
        node(0, 173, 139, 74, 'ANDROID', ['Caméra + Flutter', 'Identité et certificat', 'du serveur mémorisés'], LIME)
        node(188, 172, 309, 64, 'GATEWAY / FASTAPI', ['Séquence, consentement, qualité, sessions', 'HTTPS + WebSocket TLS : 8443'])
        arrow(139, 202, 188, 202)
        c.setFont('Vault', 7.2)
        c.drawCentredString(163, 212, 'TLS')
        node(188, 79, 146, 64, 'VISION / PYTHON', ['MediaPipe → repères', 'gRPC privé : 50051'])
        node(351, 79, 146, 64, 'SCORE / MATLAB', ['Engine + licence du PC', 'HTTPS privé : 9910'])
        arrow(261, 172, 261, 143)
        arrow(424, 172, 424, 143)
        node(188, 21, 309, 42, 'DONNÉES LOCALES', ['SQLite • sessions en mémoire • média local'])
        node(0, 40, 139, 93, 'DÉCOUVERTE LAN', ['mDNS / UDP 5353', '_thevault._tcp.local.', 'Nom + ID + empreinte', 'IPv4 privée du poste'])
        arrow(69, 133, 69, 173)
        c.setFillColor(MUTED)
        c.setFont('VaultItalic', 8)
        c.drawString(0, 14, 'Mode local vérifié')


def flowables(block, spec, style):
    kind = block['type']
    if kind in ('p', 'h'):
        return [paragraph(block['text'], style['body' if kind == 'p' else 'h'],
                          markup=kind == 'p' and '<link ' in block['text'])]
    if kind == 'bullets':
        return [paragraph('•  ' + text, style['bullet']) for text in block['items']] + [Spacer(1, 4)]
    if kind == 'note':
        return [box(block['text'], style, title=block['title']), Spacer(1, 10)]
    if kind == 'code':
        code = paragraph(block['text'], style['code'])
        t = Table([[code]], colWidths=[WIDTH])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eef0ef')),
            ('LEFTPADDING', (0, 0), (-1, -1), 10),
            ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        return [t, Spacer(1, 8)]
    if kind == 'architecture':
        return [Architecture(), Spacer(1, 8)]
    if kind == 'toc':
        rows = []
        for i, page in enumerate(spec['pages'], start=2):
            title = escape(page['title'])
            rows.append([paragraph(f'<link href="#page-{i}" color="#172021">{title}</link>',
                                   style['toc'], markup=True), str(i)])
        t = Table(rows, colWidths=[WIDTH - 30, 30])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Vault'), ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('TEXTCOLOR', (0, 0), (-1, -1), INK), ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 1.7), ('BOTTOMPADDING', (0, 0), (-1, -1), 1.7),
            ('LINEBELOW', (0, 0), (-1, -1), .25, LINE),
        ]))
        return [paragraph('Sommaire interactif', style['h']), t]
    if kind == 'table':
        rows = [[paragraph(cell, style['headcell']) for cell in block['headers']]]
        rows += [[paragraph(str(cell), style['cell']) for cell in row] for row in block['rows']]
        widths = block.get('widths', [WIDTH / len(rows[0])] * len(rows[0]))
        widths = [w * WIDTH / sum(widths) for w in widths]
        t = Table(rows, colWidths=widths, repeatRows=1, hAlign='LEFT')
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), INK),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f2f5ef'), colors.white]),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 8), ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 7), ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
            ('LINEBELOW', (0, 0), (-1, -1), .3, LINE),
        ]))
        return [t, Spacer(1, 12)]
    raise ValueError(f'Unknown specification block: {kind}')


def footer(c, number, total, spec):
    c.setStrokeColor(LINE)
    c.setLineWidth(.5)
    c.line(MARGIN, 43, PAGE_W - MARGIN, 43)
    c.setFillColor(MUTED)
    c.setFont('Vault', 7.5)
    c.drawString(MARGIN, 29, f"THE VAULT  /  DOCUMENT {spec['revision']}  /  {spec['date']}")
    c.drawRightString(PAGE_W - MARGIN, 29, f'{number:02d} / {total:02d}')


def cover(c, spec, total):
    c.setFillColor(INK)
    c.rect(0, 286, PAGE_W, PAGE_H - 286, fill=1, stroke=0)
    c.setFillColor(LIME)
    c.rect(MARGIN, PAGE_H - 75, 36, 5, fill=1, stroke=0)
    c.setFont('VaultBold', 10)
    c.drawString(MARGIN, PAGE_H - 105, 'INGÉNIERIE BIOMÉTRIQUE / DÉMONSTRATEUR LOCAL')
    c.setFillColor(colors.white)
    c.setFont('VaultBold', 56)
    c.drawString(MARGIN - 3, 631, 'THE')
    c.drawString(MARGIN - 3, 566, 'VAULT')
    c.setFont('Vault', 21)
    c.drawString(MARGIN, 504, 'Cahier des charges')
    c.setFillColor(LIME)
    c.drawString(MARGIN, 473, 'Édition révisée 1.1')
    c.setFillColor(colors.white)
    c.setFont('Vault', 11)
    for y, line in [(414, 'Visage. Mouvement du corps. Signature aérienne.'),
                    (394, 'MediaPipe en temps réel et comparaison MATLAB.'),
                    (374, 'Un coffre. Un mème. Une intention satirique.')]:
        c.drawString(MARGIN, y, line)
    c.setFont('VaultBold', 9)
    c.setFillColor(LIME)
    c.drawString(MARGIN, 317, 'LICENCE DU POSTE  /  DÉCOUVERTE LAN  /  APK PUBLIC')
    c.setFillColor(INK)
    c.setFont('VaultBold', 12)
    c.drawString(MARGIN, 251, 'LE PLAN, L’IMPLÉMENTATION ET LES PREUVES')
    text = ('Une révision complète du document initial : architecture actuelle, écarts '
            'expliqués, installation, configuration, essais guidés et critères de recette. '
            'Les essais sur téléphone physique et les mesures biométriques restent à réaliser.')
    p = paragraph(text, styles()['body'])
    _, h = p.wrap(WIDTH, 100)
    p.drawOn(c, MARGIN, 225 - h)
    c.setFont('Vault', 9)
    c.setFillColor(MUTED)
    c.drawString(MARGIN, 125, f"Paquet : {spec['package']}  •  Application : {spec['application']}")
    c.drawString(MARGIN, 106, 'Original de 18 pages conservé dans le dépôt.')
    c.linkURL('https://github.com/FediMechergui/the-vault',
              (MARGIN, 71, PAGE_W - MARGIN, 88), relative=0, thickness=0)
    c.setFillColor(INK)
    c.drawString(MARGIN, 77, 'github.com/FediMechergui/the-vault')
    footer(c, 1, total, spec)


def build(source: Path, output: Path):
    spec = json.loads(source.read_text(encoding='utf-8'))
    fonts()
    style = styles()
    total = len(spec['pages']) + 1
    output.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output), pagesize=A4, pageCompression=1, invariant=1)
    c.setTitle('THE VAULT — Cahier des charges révisé 1.1')
    c.setAuthor('THE VAULT project')
    c.setSubject('Architecture, installation, configuration, validation et écarts au plan initial')
    c.setCreator('scripts/build_specification.py / ReportLab')
    c.setViewerPreference('DisplayDocTitle', 'true')
    c.bookmarkPage('cover')
    c.addOutlineEntry('THE VAULT — Édition révisée', 'cover', level=0)
    cover(c, spec, total)
    c.showPage()
    for number, page in enumerate(spec['pages'], start=2):
        c.bookmarkPage(f'page-{number}')
        c.addOutlineEntry(page['title'], f'page-{number}', level=0)
        c.setFillColor(INK)
        c.setFont('VaultBold', 8)
        c.drawString(MARGIN, PAGE_H - 34, 'THE VAULT / CAHIER DES CHARGES RÉVISÉ')
        c.setFillColor(LIME)
        c.rect(PAGE_W - MARGIN - 25, PAGE_H - 39, 25, 7, fill=1, stroke=0)
        title_style = ParagraphStyle('title', fontName='VaultBold', fontSize=22, leading=27,
                                     textColor=INK)
        title = paragraph(page['title'], title_style)
        _, title_h = title.wrap(WIDTH, 100)
        title_y = PAGE_H - 64 - title_h
        title.drawOn(c, MARGIN, title_y)
        subtitle = paragraph(page['subtitle'], style['small'])
        _, sub_h = subtitle.wrap(WIDTH, 80)
        subtitle_y = title_y - 9 - sub_h
        subtitle.drawOn(c, MARGIN, subtitle_y)
        c.setStrokeColor(LINE)
        c.line(MARGIN, subtitle_y - 14, PAGE_W - MARGIN, subtitle_y - 14)
        story = []
        for block in page['blocks']:
            story.extend(flowables(block, spec, style))
        frame = Frame(MARGIN, 59, WIDTH, subtitle_y - 24 - 59,
                      leftPadding=0, bottomPadding=0, rightPadding=0, topPadding=0)
        frame.addFromList(story, c)
        if story:
            raise ValueError(f"Page {number} overflows ({page['title']}): {len(story)} blocks remain")
        footer(c, number, total, spec)
        c.showPage()
    c.save()
    print(f'Built {total} pages: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path,
                        default=ROOT / 'docs/specification/specification-v1.1.json')
    parser.add_argument('--output', type=Path,
                        default=ROOT / 'docs/THE_VAULT_Cahier_des_charges_v1.1.pdf')
    args = parser.parse_args()
    build(args.source, args.output)
