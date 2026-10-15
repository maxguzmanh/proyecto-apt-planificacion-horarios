"""Calendario semanal PDF del profesor, construido desde datos ya autorizados."""
from io import BytesIO
import re
import unicodedata

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas


DIAS = [
    ("LU", "Lunes"), ("MA", "Martes"), ("MI", "Miércoles"),
    ("JU", "Jueves"), ("VI", "Viernes"), ("SA", "Sábado"),
    ("DO", "Domingo"),
]
HORA_INICIAL = 6
HORA_FINAL = 22


def nombre_archivo_horario(profesor, periodo):
    texto = unicodedata.normalize("NFKD", f"Horario_{profesor}_{periodo.codigo}")
    texto = texto.encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9_-]+", "_", texto).strip("_") + ".pdf"


def _minutos(hora):
    return hora.hour * 60 + hora.minute


def _recortar(texto, ancho, fuente="Helvetica", tamano=6.5):
    texto = str(texto)
    if stringWidth(texto, fuente, tamano) <= ancho:
        return texto
    sufijo = "…"
    while texto and stringWidth(texto + sufijo, fuente, tamano) > ancho:
        texto = texto[:-1]
    return texto + sufijo


def _dibujar_evento(pdf, horario, x, y_superior, ancho, alto):
    pendiente = horario.aula_id is None
    fondo = colors.HexColor("#FFF7D6") if pendiente else colors.HexColor("#E9F2FF")
    borde = colors.HexColor("#E56910") if pendiente else colors.HexColor("#0C66E4")
    pdf.setFillColor(fondo)
    pdf.setStrokeColor(borde)
    pdf.setLineWidth(1.1)
    pdf.roundRect(x + 1.5, y_superior - alto + 1, ancho - 3, alto - 2, 2.5, fill=1, stroke=1)

    pdf.saveState()
    ruta = pdf.beginPath()
    ruta.rect(x + 3, y_superior - alto + 3, ancho - 6, max(alto - 6, 1))
    pdf.clipPath(ruta, stroke=0, fill=0)
    izquierda = x + 5
    disponible = ancho - 10
    cursor = y_superior - 10
    lineas = [
        (horario.oferta.asignatura.nombre, "Helvetica-Bold", 6.8),
        (f"{horario.hora_inicio:%H:%M}–{horario.hora_fin:%H:%M}", "Helvetica", 6.2),
        (horario.sede.nombre, "Helvetica", 6.2),
        (horario.aula.nombre if horario.aula_id else "Aula pendiente", "Helvetica", 6.2),
    ]
    pdf.setFillColor(colors.HexColor("#172B4D"))
    limite = y_superior - alto + 4
    for valor, fuente, tamano in lineas:
        if cursor < limite:
            break
        pdf.setFont(fuente, tamano)
        pdf.drawString(izquierda, cursor, _recortar(valor, disponible, fuente, tamano))
        cursor -= tamano + 2
    pdf.restoreState()


def crear_pdf_horario_profesor(profesor, periodo, horarios):
    buffer = BytesIO()
    ancho_pagina, alto_pagina = landscape(A4)
    pdf = canvas.Canvas(buffer, pagesize=(ancho_pagina, alto_pagina), pageCompression=0)
    pdf.setTitle(f"Horario de {profesor}")
    pdf.setAuthor("UniPlan")

    margen = 30
    pdf.setFillColor(colors.HexColor("#172B4D"))
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawCentredString(ancho_pagina / 2, alto_pagina - 34, "Horario semanal")
    etiqueta_profesor = "Profesor:"
    etiqueta_periodo = "Periodo académico:"
    valor_periodo = periodo.codigo if periodo.nombre.strip() == periodo.codigo else f"{periodo.nombre} ({periodo.codigo})"
    pdf.setFont("Helvetica-Bold", 9.5)
    pdf.drawString(margen, alto_pagina - 57, etiqueta_profesor)
    pdf.drawString(margen, alto_pagina - 72, etiqueta_periodo)
    pdf.setFont("Helvetica", 9.5)
    pdf.drawString(margen + stringWidth(etiqueta_profesor, "Helvetica-Bold", 9.5) + 5, alto_pagina - 57, str(profesor))
    pdf.drawString(margen + stringWidth(etiqueta_periodo, "Helvetica-Bold", 9.5) + 5, alto_pagina - 72, valor_periodo)

    izquierda, derecha = margen, ancho_pagina - margen
    superior, inferior = alto_pagina - 103, 39
    alto_cabecera, ancho_horas = 22, 39
    alto_horas = superior - inferior - alto_cabecera
    ancho_dia = (derecha - izquierda - ancho_horas) / len(DIAS)
    puntos_hora = alto_horas / (HORA_FINAL - HORA_INICIAL)
    tope_horas = superior - alto_cabecera

    pdf.setFillColor(colors.HexColor("#172B4D"))
    pdf.rect(izquierda, superior - alto_cabecera, derecha - izquierda, alto_cabecera, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont("Helvetica-Bold", 7.5)
    for indice, (_, nombre) in enumerate(DIAS):
        centro = izquierda + ancho_horas + (indice + 0.5) * ancho_dia
        pdf.drawCentredString(centro, superior - 14, nombre)

    pdf.setStrokeColor(colors.HexColor("#B3B9C4"))
    pdf.setLineWidth(0.45)
    for indice in range(len(DIAS) + 1):
        x = izquierda + ancho_horas + indice * ancho_dia
        pdf.line(x, inferior, x, superior)
    pdf.line(izquierda, inferior, izquierda, superior)
    pdf.line(izquierda + ancho_horas, inferior, izquierda + ancho_horas, superior)

    for media_hora in range((HORA_FINAL - HORA_INICIAL) * 2 + 1):
        y = tope_horas - media_hora * puntos_hora / 2
        es_hora = media_hora % 2 == 0
        pdf.setStrokeColor(colors.HexColor("#B3B9C4") if es_hora else colors.HexColor("#DFE1E6"))
        pdf.setLineWidth(0.45 if es_hora else 0.25)
        # Las horas completas cierran también la celda del eje horario;
        # las medias horas solo dividen el área de los días.
        pdf.line(izquierda if es_hora else izquierda + ancho_horas, y, derecha, y)
        if es_hora and media_hora < (HORA_FINAL - HORA_INICIAL) * 2:
            hora = HORA_INICIAL + media_hora // 2
            pdf.setFillColor(colors.HexColor("#44546F"))
            pdf.setFont("Helvetica", 6.5)
            # Centrar la etiqueta dentro de su franja evita que se monte
            # sobre la línea de inicio o término de un evento.
            pdf.drawCentredString(
                izquierda + ancho_horas / 2,
                y - puntos_hora / 2 - 2.2,
                f"{hora:02d}:00",
            )

    indice_dia = {codigo: indice for indice, (codigo, _) in enumerate(DIAS)}
    for horario in horarios:
        inicio = max(_minutos(horario.hora_inicio), HORA_INICIAL * 60)
        fin = min(_minutos(horario.hora_fin), HORA_FINAL * 60)
        if horario.dia not in indice_dia or fin <= inicio:
            continue
        x = izquierda + ancho_horas + indice_dia[horario.dia] * ancho_dia
        y = tope_horas - ((inicio - HORA_INICIAL * 60) / 60) * puntos_hora
        alto = ((fin - inicio) / 60) * puntos_hora
        _dibujar_evento(pdf, horario, x, y, ancho_dia, alto)

    pdf.setFillColor(colors.HexColor("#626F86"))
    pdf.setFont("Helvetica", 7.5)
    pdf.drawString(margen, 18, "UniPlan · Portal Profesor")
    pdf.drawRightString(ancho_pagina - margen, 18, f"{profesor} · {periodo.codigo}")
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()
