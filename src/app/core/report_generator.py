from pathlib import Path

import pandas as pd
from docx import Document
from docx.document import Document as DocumentObject
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Pt, RGBColor
from docx.styles.style import ParagraphStyle
from docx.table import Table, _Cell
from docx.text.run import Run

FONT_NAME = "Times New Roman"
FONT_SIZE = Pt(14)
TABLE_FONT_SIZE = Pt(11)


def apply_font_to_run(
    run: Run,
    font_name: str = FONT_NAME,
    font_size: Pt = FONT_SIZE,
    bold: bool = False,
) -> None:
    """Применяет Times New Roman с поддержкой кириллицы к фрагменту текста."""
    run.font.name = font_name
    run.font.size = font_size
    run.font.bold = bold

    r_pr = run._r.get_or_add_rPr()
    r_fonts = r_pr.get_or_add_rFonts()
    r_fonts.set(qn("w:ascii"), font_name)
    r_fonts.set(qn("w:hAnsi"), font_name)
    r_fonts.set(qn("w:cs"), font_name)
    r_fonts.set(qn("w:eastAsia"), font_name)


def set_cell_background(cell: _Cell, hex_color: str) -> None:
    """Устанавливает цвет заливки ячейки Word."""
    shading_elm = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{hex_color}"/>')
    cell._tc.get_or_add_tcPr().append(shading_elm)


def format_cell_text(cell: _Cell, text: str, bold: bool = False) -> None:
    """Форматирует текст внутри ячейки таблицы шрифтом Times New Roman."""
    cell.text = text
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if p.runs:
        apply_font_to_run(p.runs[0], FONT_NAME, TABLE_FONT_SIZE, bold=bold)


def insert_df_table(
    doc: DocumentObject,
    df: pd.DataFrame,
    x_alerts: list[bool],
    is_extended: bool = False,
) -> Table:
    """Вставляет стилизованную таблицу pandas DataFrame в Word документ."""
    table = doc.add_table(rows=len(df) + 1, cols=len(df.columns))
    table.style = "Table Grid"

    # 1. Заголовки
    for col_idx, col_name in enumerate(df.columns):
        cell = table.cell(0, col_idx)
        set_cell_background(cell, "E0E7FF")
        format_cell_text(cell, str(col_name), bold=True)

    # 2. Строки данных
    x_col_idx = list(df.columns).index("x") if "x" in df.columns else -1

    for row_idx in range(len(df)):
        for col_idx in range(len(df.columns)):
            cell = table.cell(row_idx + 1, col_idx)
            val: object = df.iloc[row_idx, col_idx]
            val_str = (
                f"{float(val):.4f}"
                if isinstance(val, (float, int)) and not isinstance(val, bool)
                else str(val)
            )

            if col_idx == x_col_idx and row_idx < len(x_alerts) and x_alerts[row_idx]:
                set_cell_background(cell, "FF8A8A")

            format_cell_text(cell, val_str)

    # 3. Для расширенной таблицы объединяем столбец W на 20 строк
    if is_extended and "W" in df.columns:
        w_col_idx = list(df.columns).index("W")
        merged_cell = table.cell(1, w_col_idx).merge(table.cell(len(df), w_col_idx))
        merged_cell.text = ""
        w_val_obj: object = df["W"].iloc[0]
        w_float = float(w_val_obj) if isinstance(w_val_obj, (float, int)) else 0.0
        format_cell_text(merged_cell, f"{w_float:.4f}", bold=True)

    return table


def generate_docx_report(
    template_path: Path,
    output_path: Path,
    report_data: dict[str, str],
    preview_df: pd.DataFrame,
    extended_df: pd.DataFrame,
    x_alerts: list[bool],
    violating_c: list[int],
) -> None:
    """Генерирует финальный отчет Word с форматированием Times New Roman, 14."""
    if not template_path.exists():
        raise FileNotFoundError(f"Файл шаблона не найден: {template_path}")

    doc = Document(str(template_path))

    # Задаем глобальный стиль Normal по умолчанию: Times New Roman, 14 pt
    style_normal = doc.styles["Normal"]
    if isinstance(style_normal, ParagraphStyle):
        style_normal.font.name = FONT_NAME
        style_normal.font.size = FONT_SIZE

    # Подстановка текстовых меток во все параграфы
    for paragraph in doc.paragraphs:
        for key, val in report_data.items():
            tag = f"{{{{ {key} }}}}"
            tag_no_space = f"{{{{{key}}}}}"
            if tag in paragraph.text:
                paragraph.text = paragraph.text.replace(tag, val)
            if tag_no_space in paragraph.text:
                paragraph.text = paragraph.text.replace(tag_no_space, val)
        for run in paragraph.runs:
            apply_font_to_run(run, FONT_NAME, FONT_SIZE, bold=bool(run.bold))

    # И в таблицы шаблона
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for key, val in report_data.items():
                    tag = f"{{{{ {key} }}}}"
                    tag_no_space = f"{{{{{key}}}}}"
                    if tag in cell.text:
                        cell.text = cell.text.replace(tag, val)
                    if tag_no_space in cell.text:
                        cell.text = cell.text.replace(tag_no_space, val)
                for p in cell.paragraphs:
                    for run in p.runs:
                        apply_font_to_run(run, FONT_NAME, FONT_SIZE, bold=bool(run.bold))

    target_p = None
    for p in doc.paragraphs:
        if "{{ CONTENT }}" in p.text or "{{CONTENT}}" in p.text:
            target_p = p
            p.text = ""
            break

    # Таблица превью
    p_title = doc.add_paragraph() if target_p is None else target_p.insert_paragraph_before()
    run_t = p_title.add_run("Таблица измерений (превью):")
    apply_font_to_run(run_t, FONT_NAME, FONT_SIZE, bold=True)

    _ = insert_df_table(doc, preview_df, x_alerts, is_extended=False)

    # Строка статуса
    p_status = doc.add_paragraph()
    p_status.paragraph_format.space_before = Pt(14)
    p_status.paragraph_format.space_after = Pt(14)

    if not violating_c:
        run_status = p_status.add_run("При проверке не обнаружено нарушений.")
        apply_font_to_run(run_status, FONT_NAME, FONT_SIZE, bold=True)
        run_status.font.color.rgb = RGBColor(0x15, 0x80, 0x3D)
    else:
        c_list_str = ", ".join(str(c) for c in violating_c)
        run_status = p_status.add_run(f"При проверке обнаружены нарушения на C: {c_list_str}")
        apply_font_to_run(run_status, FONT_NAME, FONT_SIZE, bold=True)
        run_status.font.color.rgb = RGBColor(0xB9, 0x1C, 0x1C)

        for idx, c_val in enumerate(violating_c, 1):
            p_ext = doc.add_paragraph()
            p_ext.paragraph_format.space_before = Pt(16)
            run_ext = p_ext.add_run(f"Расширенная таблица для нарушения №{idx} (C = {c_val}):")
            apply_font_to_run(run_ext, FONT_NAME, FONT_SIZE, bold=True)

            _ = insert_df_table(doc, extended_df, x_alerts, is_extended=True)

    doc.save(str(output_path))
