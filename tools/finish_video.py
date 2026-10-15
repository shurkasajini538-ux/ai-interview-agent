"""Mux recorded synthetic-data UI with disclosed system Mandarin narration."""
from pathlib import Path
import json,re,subprocess,wave
ROOT=Path(__file__).resolve().parents[1]
tmp=ROOT/'tmp/video';out=ROOT/'release';out.mkdir(exist_ok=True)
timings=json.loads((tmp/'timing.json').read_text(encoding='utf-8'))
chapters=json.loads((ROOT/'docs/演示脚本.json').read_text(encoding='utf-8'))
def run(args):subprocess.run(args,check=True,cwd=ROOT)
def stamp(t):
 t=round(t*100);return f'{t//360000}:{t//6000%60:02}:{t//100%60:02}.{t%100:02}'
ass='''[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080
WrapStyle: 2
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,32,&H00FFFFFF,&H00FFFFFF,&H80202020,&H80202020,0,0,0,0,100,100,0,0,3,2,0,2,90,90,60,1
Style: Heading,Microsoft YaHei,26,&H00314B17,&H00314B17,&H00F0F6F5,&H00F0F6F5,0,0,0,0,100,100,0,0,3,6,0,8,90,90,10,1
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
start=0;lines=[]
for i,(seconds,chapter) in enumerate(zip(timings,chapters)):
 run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(tmp/f'chapter-{i}.wav'),'-af','atempo=1.01,apad','-t',str(seconds),'-ar','48000','-ac','1',str(tmp/f'padded-{i}.wav')])
 lines.append(f"file 'padded-{i}.wav'")
 with wave.open(str(tmp/f'chapter-{i}.wav')) as wav:duration=wav.getnframes()/wav.getframerate()/1.01
 assert duration <= seconds, f'Narration exceeds chapter {i}'
 phrases=[part for sentence in re.findall(r'[^。！？]+[。！？]?',chapter['text']) for part in [sentence[j:j+36] for j in range(0,len(sentence),36)]]
 total=sum(len(x) for x in phrases);cursor=start
 ass+=f"Dialogue: 1,{stamp(start)},{stamp(start+seconds)},Heading,,0,0,0,,{i+1:02}  {chapter['title']}\n"
 for phrase in phrases:
  end=cursor+duration*len(phrase)/total
  ass+=f'Dialogue: 0,{stamp(cursor)},{stamp(end)},Default,,0,0,0,,{phrase}\n';cursor=end
 start+=seconds
(tmp/'captions.ass').write_text(ass,encoding='utf-8-sig')
(tmp/'audio-list.txt').write_text('\n'.join(lines),encoding='utf-8')
run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(tmp/'audio-list.txt'),'-c','copy',str(tmp/'narration.wav')])
dest=out/'面试工坊_演示视频_2.0.1.mp4'
run(['ffmpeg','-hide_banner','-loglevel','warning','-y','-i',str(tmp/'screen.webm'),'-i',str(tmp/'narration.wav'),'-vf','ass=tmp/video/captions.ass','-c:v','libx264','-preset','fast','-crf','23','-pix_fmt','yuv420p','-c:a','aac','-b:a','160k','-t',str(sum(timings)),'-movflags','+faststart',str(dest)])
probe=json.loads(subprocess.check_output(['ffprobe','-v','quiet','-show_streams','-show_format','-of','json',str(dest)],text=True,encoding='utf-8'))
video=next(s for s in probe['streams'] if s['codec_type']=='video')
assert video['width']==1920 and video['height']==1080
assert 300<=float(probe['format']['duration'])<=480
(ROOT/'verification/video-specification.json').write_text(json.dumps({'version':'2.0.1','width':video['width'],'height':video['height'],'duration_seconds':float(probe['format']['duration']),'video_codec':video['codec_name'],'audio_codec':'aac','synthetic_narration':True,'synthetic_data':True,'demo_mode':'offline','subtitle_timing':'按句长近似对齐合成旁白，正式提交前人工试听复核'},ensure_ascii=False,indent=2),encoding='utf-8')
print(dest)
