import os
import re
from pathlib import Path
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_shading(cell, color_hex):
    """Set background color of a cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}"/>')
    tcPr.append(shd)

def set_cell_margins(cell, top=100, bottom=100, left=150, right=150):
    """Set inner padding of a cell in dxa (1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}>'
                      f'<w:top w:w="{top}" w:type="dxa"/>'
                      f'<w:bottom w:w="{bottom}" w:type="dxa"/>'
                      f'<w:left w:w="{left}" w:type="dxa"/>'
                      f'<w:right w:w="{right}" w:type="dxa"/>'
                      f'</w:tcMar>')
    tcPr.append(tcMar)

def set_cell_borders(cell, top="CCCCCC", bottom="CCCCCC", left=None, right=None):
    """Set borders of a cell."""
    tcPr = cell._tc.get_or_add_tcPr()
    border_xml = f'<w:tcBorders {nsdecls("w")}>'
    if top:
        border_xml += f'<w:top w:val="single" w:sz="4" w:space="0" w:color="{top}"/>'
    else:
        border_xml += '<w:top w:val="none"/>'
    if bottom:
        border_xml += f'<w:bottom w:val="single" w:sz="4" w:space="0" w:color="{bottom}"/>'
    else:
        border_xml += '<w:bottom w:val="none"/>'
    if left:
        border_xml += f'<w:left w:val="single" w:sz="4" w:space="0" w:color="{left}"/>'
    else:
        border_xml += '<w:left w:val="none"/>'
    if right:
        border_xml += f'<w:right w:val="single" w:sz="4" w:space="0" w:color="{right}"/>'
    else:
        border_xml += '<w:right w:val="none"/>'
    border_xml += '</w:tcBorders>'
    tcPr.append(parse_xml(border_xml))

def apply_inline_formatting(paragraph, text, base_font_size=10.5, is_italic_base=False):
    """
    Parse inline bold (**text**), code (`text`), italic (*text*), math ($...$), and links ([text](url)).
    """
    # Tokenize text
    # Pattern for **bold**, `code`, *italic*, [text](url)
    tokens = re.split(r'(\*\*.*?\*\*|`.*?`|\*.*?\*|\[.*?\]\(.*?\))', text)
    
    for token in tokens:
        if not token:
            continue
        if token.startswith('**') and token.endswith('**') and len(token) >= 4:
            content = token[2:-2]
            run = paragraph.add_run(content)
            run.bold = True
            run.font.name = 'Calibri'
            run.font.size = Pt(base_font_size)
            run.font.color.rgb = RGBColor(30, 41, 59)
        elif token.startswith('`') and token.endswith('`') and len(token) >= 2:
            content = token[1:-1]
            run = paragraph.add_run(content)
            run.font.name = 'Consolas'
            run.font.size = Pt(base_font_size * 0.9)
            run.font.color.rgb = RGBColor(190, 24, 93)  # Rose/Pink for inline code
        elif token.startswith('*') and token.endswith('*') and len(token) >= 2:
            content = token[1:-1]
            run = paragraph.add_run(content)
            run.italic = True
            run.font.name = 'Calibri'
            run.font.size = Pt(base_font_size)
            run.font.color.rgb = RGBColor(71, 85, 105)
        elif token.startswith('[') and '](' in token and token.endswith(')'):
            m = re.match(r'\[(.*?)\]\((.*?)\)', token)
            if m:
                label, url = m.groups()
                run = paragraph.add_run(label)
                run.font.name = 'Calibri'
                run.font.size = Pt(base_font_size)
                run.font.color.rgb = RGBColor(2, 132, 199)  # Blue link
                run.underline = True
            else:
                run = paragraph.add_run(token)
                run.font.name = 'Calibri'
                run.font.size = Pt(base_font_size)
        else:
            run = paragraph.add_run(token)
            run.font.name = 'Calibri'
            run.font.size = Pt(base_font_size)
            if is_italic_base:
                run.italic = True
                run.font.color.rgb = RGBColor(100, 116, 139)
            else:
                run.font.color.rgb = RGBColor(51, 65, 85)

def markdown_to_docx(md_path: Path, docx_path: Path):
    print(f"Converting {md_path.name} -> {docx_path.name}...")
    doc = docx.Document()
    
    # Configure 1-inch margins
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin = Inches(1.0)
        section.right_margin = Inches(1.0)
        section.page_width = Inches(8.5)
        section.page_height = Inches(11.0)
        
        # Configure Header and Footer
        header = section.header
        hp = header.paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        hrun = hp.add_run("MatChain: AI Materials Discovery & Decentralized IP Platform")
        hrun.font.name = "Calibri"
        hrun.font.size = Pt(8.5)
        hrun.font.color.rgb = RGBColor(148, 163, 184)
        
        footer = section.footer
        fp = footer.paragraphs[0]
        fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        frun = fp.add_run("Final Year Computer Engineering Capstone Project Report | Academic Evaluation")
        frun.font.name = "Calibri"
        frun.font.size = Pt(8.5)
        frun.font.color.rgb = RGBColor(148, 163, 184)

    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    in_code_block = False
    code_block_lines = []
    code_lang = ""
    
    in_table = False
    table_lines = []

    i = 0
    while i < len(lines):
        raw_line = lines[i]
        line = raw_line.rstrip('\r\n')
        
        # Handle code blocks
        if line.startswith('```'):
            if not in_code_block:
                in_code_block = True
                code_lang = line[3:].strip()
                code_block_lines = []
            else:
                in_code_block = False
                # Render code block as a 1x1 styled table
                code_text = '\n'.join(code_block_lines)
                table = doc.add_table(rows=1, cols=1)
                table.alignment = WD_TABLE_ALIGNMENT.CENTER
                cell = table.cell(0, 0)
                set_cell_shading(cell, "F8FAFC")
                set_cell_borders(cell, top="E2E8F0", bottom="E2E8F0", left="0284C7", right="E2E8F0")
                set_cell_margins(cell, top=140, bottom=140, left=200, right=200)
                
                cp = cell.paragraphs[0]
                cp.paragraph_format.space_before = Pt(0)
                cp.paragraph_format.space_after = Pt(0)
                crun = cp.add_run(code_text)
                crun.font.name = "Consolas"
                crun.font.size = Pt(9.0)
                crun.font.color.rgb = RGBColor(15, 23, 42)
                
                # Space after table
                sp = doc.add_paragraph()
                sp.paragraph_format.space_before = Pt(0)
                sp.paragraph_format.space_after = Pt(4)
                code_block_lines = []
            i += 1
            continue

        if in_code_block:
            code_block_lines.append(line)
            i += 1
            continue

        # Handle tables
        if line.strip().startswith('|') and line.strip().endswith('|'):
            if not in_table:
                in_table = True
                table_lines = [line]
            else:
                table_lines.append(line)
            i += 1
            continue
        else:
            if in_table:
                # Finish and render table
                in_table = False
                # Parse markdown table
                parsed_rows = []
                for tline in table_lines:
                    # check if separator line
                    stripped = tline.strip()
                    if re.match(r'^\|(\s*:?-+:?\s*\|)+$', stripped):
                        continue
                    cells = [c.strip() for c in stripped[1:-1].split('|')]
                    parsed_rows.append(cells)
                
                if parsed_rows:
                    num_cols = max(len(r) for r in parsed_rows)
                    # Normalize row widths
                    for r in parsed_rows:
                        while len(r) < num_cols:
                            r.append('')
                    
                    table = doc.add_table(rows=len(parsed_rows), cols=num_cols)
                    table.alignment = WD_TABLE_ALIGNMENT.CENTER
                    
                    for row_idx, row_data in enumerate(parsed_rows):
                        row = table.rows[row_idx]
                        is_header = (row_idx == 0)
                        for col_idx, cell_data in enumerate(row_data):
                            cell = row.cells[col_idx]
                            set_cell_margins(cell, top=120, bottom=120, left=140, right=140)
                            
                            if is_header:
                                set_cell_shading(cell, "1E3A8A")  # Deep Blue
                                set_cell_borders(cell, top="1E3A8A", bottom="1E3A8A", left="1E3A8A", right="1E3A8A")
                            else:
                                if row_idx % 2 == 1:
                                    set_cell_shading(cell, "FFFFFF")
                                else:
                                    set_cell_shading(cell, "F8FAFC")  # Alternate row
                                set_cell_borders(cell, top="E2E8F0", bottom="E2E8F0", left="E2E8F0", right="E2E8F0")
                            
                            cp = cell.paragraphs[0]
                            cp.paragraph_format.space_before = Pt(0)
                            cp.paragraph_format.space_after = Pt(0)
                            if is_header:
                                run = cp.add_run(cell_data)
                                run.bold = True
                                run.font.name = "Calibri"
                                run.font.size = Pt(9.5)
                                run.font.color.rgb = RGBColor(255, 255, 255)
                            else:
                                apply_inline_formatting(cp, cell_data, base_font_size=9.0)
                    
                    # Space after table
                    sp = doc.add_paragraph()
                    sp.paragraph_format.space_before = Pt(0)
                    sp.paragraph_format.space_after = Pt(6)
                table_lines = []

        # Empty lines
        if not line.strip():
            i += 1
            continue

        # Horizontal Rule
        if line.strip() == '---':
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(6)
            p.paragraph_format.space_after = Pt(6)
            pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="6" w:space="1" w:color="CBD5E1"/></w:pBdr>')
            p._p.get_or_add_pPr().append(pBdr)
            i += 1
            continue

        # Headings
        if line.startswith('# '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(18)
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[2:].strip())
            run.font.name = 'Calibri'
            run.font.size = Pt(22)
            run.bold = True
            run.font.color.rgb = RGBColor(15, 23, 42)  # Slate 900
            i += 1
            continue
        elif line.startswith('## '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(14)
            p.paragraph_format.space_after = Pt(4)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[3:].strip())
            run.font.name = 'Calibri'
            run.font.size = Pt(16)
            run.bold = True
            run.font.color.rgb = RGBColor(30, 58, 138)  # Blue 900
            i += 1
            continue
        elif line.startswith('### '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(10)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[4:].strip())
            run.font.name = 'Calibri'
            run.font.size = Pt(13)
            run.bold = True
            run.font.color.rgb = RGBColor(3, 105, 161)  # Sky 700
            i += 1
            continue
        elif line.startswith('#### '):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(8)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            run = p.add_run(line[5:].strip())
            run.font.name = 'Calibri'
            run.font.size = Pt(11)
            run.bold = True
            run.font.color.rgb = RGBColor(71, 85, 105)  # Slate 600
            i += 1
            continue

        # Blockquote (> text)
        if line.startswith('> '):
            p = doc.add_paragraph()
            p.paragraph_format.left_indent = Inches(0.4)
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            apply_inline_formatting(p, line[2:].strip(), base_font_size=10.0, is_italic_base=True)
            i += 1
            continue

        # Bullet lists (- or *)
        if re.match(r'^[\*\-]\s+', line):
            text = re.sub(r'^[\*\-]\s+', '', line)
            p = doc.add_paragraph(style='List Bullet')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            apply_inline_formatting(p, text, base_font_size=10.5)
            i += 1
            continue

        # Numbered lists (1. 2. etc)
        m_num = re.match(r'^(\d+)\.\s+(.*)', line)
        if m_num:
            text = m_num.group(2)
            p = doc.add_paragraph(style='List Number')
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after = Pt(2)
            apply_inline_formatting(p, text, base_font_size=10.5)
            i += 1
            continue

        # Normal Paragraph
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.15
        apply_inline_formatting(p, line, base_font_size=10.5)
        i += 1

    doc.save(str(docx_path))
    print(f"Successfully generated {docx_path.name}")

def main():
    reports_dir = Path(r"d:\Matchain\docs\reports")
    files = [
        ("Testing_and_Validation_Report.md", "Testing_and_Validation_Report.docx"),
        ("Performance_Analysis_and_Result_Report.md", "Performance_Analysis_and_Result_Report.docx"),
        ("Deployment_Report_and_User_Manual.md", "Deployment_Report_and_User_Manual.docx")
    ]
    
    for md_name, docx_name in files:
        md_file = reports_dir / md_name
        docx_file = reports_dir / docx_name
        if md_file.exists():
            markdown_to_docx(md_file, docx_file)
        else:
            print(f"Error: {md_file} does not exist!")

if __name__ == "__main__":
    main()

