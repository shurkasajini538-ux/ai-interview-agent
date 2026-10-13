"""Real OCR smoke test with a synthetic Chinese resume image and scanned PDF."""
import io
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw, ImageFont
import pymupdf
from studio.resumes import extract_document

root = Path(__file__).resolve().parents[1]
out = root/'verification'
out.mkdir(exist_ok=True)
image = Image.new('RGB', (1400, 1350), 'white')
draw = ImageDraw.Draw(image)
font = ImageFont.truetype('C:/Windows/Fonts/msyh.ttc', 38)
lines = ['模拟简历 · OCR 验收样本', '姓名：测试同学', '教育背景：示例大学 计算机科学与技术 本科',
         '项目经历：校园图书借阅平台', '使用 Python、Flask、MySQL 实现后端接口。',
         '我负责数据表设计、异常处理与接口测试。', '通过 12 个测试用例验证重复借阅与参数校验。',
         '技能：Python、MySQL、Git、Linux']
for i, line in enumerate(lines):
    draw.text((65, 70+i*130), line, fill='#20352b', font=font)
b = io.BytesIO()
image.save(b, 'PNG')
png = b.getvalue()
(out/'OCR模拟简历.png').write_bytes(png)
text, warnings = extract_document('resume.png', png)
assert 'Python' in text and '测试' in text and '12' in text, text
with pymupdf.open() as pdf:
    page = pdf.new_page(width=700, height=675)
    page.insert_image(page.rect, stream=png)
    scan = pdf.tobytes()
(out/'扫描PDF模拟简历.pdf').write_bytes(scan)
pdf_text, pdf_warnings = extract_document('scanned.pdf', scan)
assert 'Python' in pdf_text and '测试' in pdf_text, pdf_text
result = {'image_ocr':'passed', 'scanned_pdf_ocr':'passed', 'image_text':text,
          'pdf_text':pdf_text, 'warnings':warnings+pdf_warnings}
(out/'ocr-results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print('Image OCR and scanned PDF OCR passed with synthetic Chinese resume.')
