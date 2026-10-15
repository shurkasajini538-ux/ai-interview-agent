"""Document extraction and evidence-preserving resume parsing."""
import io
import re
import threading
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

MAX_UPLOAD = 12 * 1024 * 1024
MAX_TEXT = 60000
SKILLS = ['Python', 'JavaScript', 'TypeScript', 'Java', 'C++', 'C#', 'Go', 'Rust',
          'SQL', 'MySQL', 'PostgreSQL', 'Redis', 'MongoDB', 'Linux', 'Git', 'Docker',
          'Kubernetes', 'Vue', 'React', 'Flask', 'Django', 'FastAPI', 'Spring',
          'PyTorch', 'TensorFlow', 'Paddle', 'Excel', 'Tableau', 'Power BI',
          '机器学习', '深度学习', '数据分析', '产品设计', '用户研究', 'Figma', 'RAG',
          'openJiuwen', 'openEuler', 'HTML', 'CSS', 'Node.js', 'MATLAB', 'SPSS']
_ocr = None
_ocr_lock = threading.Lock()


def clean_text(text):
    text = text.replace('\x00', '').replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{4,}', '\n\n\n', text).strip()
    if len(text) < 20:
        raise ValueError('可识别的简历内容不足 20 字，请补充文字或上传更清晰的文件。')
    if len(text) > MAX_TEXT:
        raise ValueError('简历超过 60,000 字，请精简后导入。')
    return text


def ocr_image(data):
    global _ocr
    try:
        import numpy as np
        from PIL import Image, ImageOps
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        raise ValueError('尚未安装图片识别依赖，请运行「安装依赖.cmd」。') from None
    with Image.open(io.BytesIO(data)) as im:
        if im.width * im.height > 30000000:
            raise ValueError('图片像素过大，请缩小到 3000 万像素以内。')
        im = ImageOps.exif_transpose(im).convert('RGB')
        im.thumbnail((2600, 3600))
        pixels = np.asarray(im)[:, :, ::-1].copy()
    with _ocr_lock:
        if _ocr is None:
            # Limit CPU usage so local OCR does not monopolize the desktop.
            _ocr = RapidOCR(intra_op_num_threads=2, inter_op_num_threads=2)
        result, _ = _ocr(pixels)
    return '\n'.join(item[1] for item in (result or []))


def extract_document(filename, data):
    if not data or len(data) > MAX_UPLOAD:
        raise ValueError('请选择非空文件，单个文件最大 12 MB。')
    ext = Path(filename).suffix.lower()
    warnings = []
    if ext in ('.txt', '.md'):
        text = None
        for encoding in ('utf-8-sig', 'gb18030', 'utf-16'):
            try:
                text = data.decode(encoding)
                break
            except UnicodeError:
                continue
        if text is None:
            raise ValueError('无法识别文本编码，请保存为 UTF-8 后重试。')
    elif ext == '.docx':
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if sum(x.file_size for x in z.infolist()) > 40 * 1024 * 1024:
                    raise ValueError('Word 文件解压后过大，请移除大图片。')
                xml = z.read('word/document.xml')
                if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:
                    raise ValueError('不支持包含外部实体的 Word 文件。')
                root = ET.fromstring(xml)
                ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                text = '\n'.join(''.join(p.itertext()) for p in root.findall('.//w:p', ns))
            warnings.append('已提取 Word 正文和表格文字；嵌入图片中的文字请另行导入图片。')
        except (zipfile.BadZipFile, KeyError, ET.ParseError):
            raise ValueError('这不是有效的 DOCX 文件，请用 Word 重新另存为 .docx。') from None
    elif ext == '.pdf':
        try:
            import pymupdf as fitz
        except ImportError:
            raise ValueError('尚未安装 PDF 依赖，请运行「安装依赖.cmd」。') from None
        try:
            with fitz.open(stream=data, filetype='pdf') as doc:
                if doc.needs_pass:
                    raise ValueError('PDF 已加密，请解除密码后再导入。')
                if len(doc) > 30:
                    raise ValueError('最多支持 30 页 PDF，请先保留与简历有关的页面。')
                parts, scan_pages = [], 0
                for page in doc:
                    part = page.get_text('text', sort=True).strip()
                    if len(part) < 25:
                        scan_pages += 1
                        if scan_pages > 6:
                            raise ValueError('扫描 PDF 最多识别 6 页，请拆分后导入。')
                        pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8))
                        part = ocr_image(pix.tobytes('png'))
                    parts.append(part)
                text = '\n\n'.join(parts)
                if scan_pages:
                    warnings.append(f'已对 {scan_pages} 页进行本地 OCR，请核对姓名、日期和数字。')
        except ValueError:
            raise
        except Exception:
            raise ValueError('PDF 解析失败，请检查文件是否损坏，或改用 Word / 文字导入。') from None
    elif ext in ('.png', '.jpg', '.jpeg', '.webp', '.bmp'):
        try:
            text = ocr_image(data)
        except ValueError:
            raise
        except Exception:
            raise ValueError('图片识别失败，请使用清晰、正向的简历图片。') from None
        warnings.append('已在本机进行 OCR，请核对文字和数字，特别是多栏排版。')
    else:
        raise ValueError('支持 PDF、DOCX、PNG、JPG、WEBP、TXT、MD；旧版 DOC 请另存为 DOCX。')
    return clean_text(text), warnings


def parse_resume(text):
    text = clean_text(text)
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    name_match = re.search(r'(?:姓名|Name)\s*[:：]\s*([^｜|\n,，]{2,24})', text, re.I)
    name = name_match.group(1).strip() if name_match else ''
    education = next((d for d in ['博士', '硕士', '本科', '大专', '高中'] if d in text), '')
    skills = []
    for skill in SKILLS:
        pattern = re.escape(skill)
        if skill.isascii():
            pattern = r'(?<![A-Za-z])' + pattern + r'(?![A-Za-z])'
        if re.search(pattern, text, re.I):
            skills.append(skill)
    projects = []
    for i, line in enumerate(lines):
        stripped = re.sub(r'^[#\s\d.、-]+', '', line).strip()
        explicit = re.search(r'^项目(?:经历|经验)?\s*\d*\s*[:：]', stripped)
        title_like = (len(stripped) <= 48 and
                      re.search(r'(?:项目|系统|平台|小程序|工具|网站)$', stripped) and
                      not re.search(r'[:：。；;，、]|课程|技能|目前|使用|负责|完成|需要|验证', stripped))
        if explicit or title_like:
            title = re.sub(r'^项目(?:经历|经验)?\s*\d*\s*[:：]\s*', '', stripped)
            if len(title) > 3 and title not in [p['title'] for p in projects]:
                projects.append({'title': title[:100], 'evidence': '\n'.join(lines[i:i+4])[:700]})
    chunks = []
    for start in range(0, len(text), 550):
        chunks.append(text[start:start+750])
    contacts = {'email': bool(re.search(r'[\w.+-]+@[\w.-]+\.[A-Za-z]+', text)),
                'phone': bool(re.search(r'(?<!\d)1[3-9]\d{9}(?!\d)', text))}
    metrics = re.findall(r'\d+(?:\.\d+)?\s*(?:%|ms|秒|分钟|小时|人|次|个|万|QPS|倍)', text, re.I)
    return {'name': name, 'education': education, 'skills': skills,
            'projects': projects[:8], 'chunks': chunks, 'contacts': contacts,
            'metrics': list(dict.fromkeys(metrics))[:12], 'character_count': len(text)}


def redact_contacts(text):
    text = re.sub(r'[\w.+-]+@[\w.-]+\.[A-Za-z]+', '[邮箱已隐藏]', text)
    text = re.sub(r'(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)', '[手机号已隐藏]', text)
    return re.sub(r'(?<!\d)\d{17}[\dXx](?!\d)', '[证件号已隐藏]', text)


def retrieve(text, query, limit=2):
    def tokens(s):
        words = set(re.findall(r'[a-z][a-z0-9+#.]+', s.lower()))
        for run in re.findall(r'[\u4e00-\u9fff]+', s):
            words.update(run[i:i+2] for i in range(len(run)-1))
        return words
    query_tokens = tokens(query)
    chunks = [text[i:i+750] for i in range(0, len(text), 550)]
    ranked = sorted(enumerate(chunks), key=lambda p: (-len(query_tokens & tokens(p[1])), p[0]))
    return [chunk for _, chunk in ranked[:limit]]
