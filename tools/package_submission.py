"""Build an allowlisted submission, excluding runtime data and credentials."""
from pathlib import Path
import hashlib,json,zipfile,subprocess

ROOT=Path(__file__).resolve().parents[1]
VERSION='2.0.1'
DEST=ROOT/'提交材料'
DEST.mkdir(exist_ok=True)
OUTPUTS={
    f'面试工坊_作品介绍与技术报告_{VERSION}.pdf':ROOT/'output/pdf'/f'面试工坊_作品介绍与技术报告_{VERSION}.pdf',
    f'面试工坊_答辩演示_{VERSION}.pptx':ROOT/'output/slides'/f'面试工坊_答辩演示_{VERSION}.pptx',
    f'面试工坊_演示视频_{VERSION}.mp4':ROOT/'release'/f'面试工坊_演示视频_{VERSION}.mp4',
    '提交填写指南.md':ROOT/'docs/提交填写指南.md',
}
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for name,source in OUTPUTS.items():
    if not source.is_file():raise FileNotFoundError(source)
    target=DEST/name
    target.write_bytes(source.read_bytes())
    assert digest(source)==digest(target)

# Only versioned application files plus the explicitly built frontend.
tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode('utf-8').split('\0')
files=[]
for relative in tracked:
    if not relative:continue
    if relative.startswith(('output/','release/','tmp/','提交材料/')):continue
    file=ROOT/relative
    if file.is_file():files.append(file)
for file in (ROOT/'frontend/dist').rglob('*'):
    if file.is_file():files.append(file)
# New materials sources and guide can be packaged before their first commit.
for relative in ['tools/package_submission.py','docs/提交填写指南.md']:
    files.append(ROOT/relative)
files=sorted(set(files))
for file in files:
    rel=file.relative_to(ROOT)
    if any(part in ('.git','.venv','node_modules','data','tmp','__pycache__') for part in rel.parts):
        raise RuntimeError(f'Forbidden runtime path: {rel}')
    if file.name.startswith('.env') and file.name!='.env.example':raise RuntimeError('Credential path')

source_zip=DEST/f'面试工坊_源码与前端构建_{VERSION}.zip'
with zipfile.ZipFile(source_zip,'w',zipfile.ZIP_DEFLATED) as archive:
    for file in files:archive.write(file,Path('AI-Interview-Studio')/file.relative_to(ROOT))
with zipfile.ZipFile(source_zip) as archive:
    assert archive.testzip() is None
    assert 'AI-Interview-Studio/frontend/dist/index.html' in archive.namelist()
    assert 'AI-Interview-Studio/app.py' in archive.namelist()
readme=DEST/'00_提交说明.md'
readme.write_text('''# 面试工坊 2.0.1 提交材料

1. 网盘上传：面试工坊_完整作品_2.0.1.zip。
2. 表单文档上传：面试工坊_作品介绍与技术报告_2.0.1.pdf。
3. 视频平台上传：面试工坊_演示视频_2.0.1.mp4，审核完成后复制公开直达链接。
4. 答辩演示_2.0.1.pptx为附加可编辑材料，随完整作品打包。
5. “提交填写指南.md”列出表单逐项填写方式和本人核对事项。

源码包包含前端生产构建；解压后安装Python3.12和Node24，双击安装依赖.cmd，再双击启动面试工坊.cmd。访问 http://127.0.0.1:8765 。可以直接使用示例简历与离线模式，在线模式需配置自己的模型Key。

此目录未包含真实用户数据、模型密钥、虚拟环境或node_modules。历史在线模型与小样本检索记录采集于2.0.0阶段，2.0.1可靠性测试与演示材料分别标明版本。

截止时间依据本人提供的表单截图：2026-10-31 15:00。正式上传、账号信息核对与提交由参赛者完成。
''',encoding='utf-8')
commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
manifest={'version':VERSION,'base_code_commit':commit,'git_branch':'codex/competition-upgrade','repository':'https://github.com/shurkasajini538-ux/ai-interview-agent','files':[]}
payload=[readme,source_zip]+[DEST/name for name in OUTPUTS]
for file in payload:manifest['files'].append({'name':file.name,'bytes':file.stat().st_size,'sha256':digest(file)})
(DEST/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
bundle=DEST/f'面试工坊_完整作品_{VERSION}.zip'
with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED) as archive:
    for file in payload+[DEST/'manifest.json']:archive.write(file,file.name)
with zipfile.ZipFile(bundle) as archive:assert archive.testzip() is None
print(json.dumps({'bundle':str(bundle),'bytes':bundle.stat().st_size,'sha256':digest(bundle),'source_files':len(files)},ensure_ascii=False))
