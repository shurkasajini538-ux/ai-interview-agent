import sys
import zipfile
from pathlib import Path
import pymupdf

root = Path(__file__).resolve().parents[1]
out = root/'verification'/'fixtures'
out.mkdir(parents=True, exist_ok=True)
text = '姓名：验收同学\n教育背景：示例大学 计算机专业 本科\n项目经历：图书借阅平台\n使用 Python 与 MySQL 完成接口，我负责测试与日志验证。\n'
(out/'文本简历.txt').write_bytes(text.encode('gb18030'))
(out/'简历.md').write_text(text, encoding='utf-8')
with zipfile.ZipFile(out/'Word简历.docx','w') as z:
    z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'+''.join('<w:p><w:r><w:t>'+line+'</w:t></w:r></w:p>' for line in text.splitlines())+'</w:body></w:document>')
with pymupdf.open() as doc:
    page = doc.new_page()
    for i,line in enumerate(text.splitlines()):
        page.insert_text((50,70+i*40),line,fontname='china-s',fontsize=14)
    doc.save(out/'文字PDF简历.pdf')
print('Synthetic Word, PDF, Markdown and GB18030 text fixtures created.')
