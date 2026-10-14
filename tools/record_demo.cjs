// Record actual local UI using synthetic data; narration is explicitly synthetic.
const {chromium}=require('../frontend/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'tmp/video');
const timings=JSON.parse(fs.readFileSync(path.join(out,'timing.json'),'utf8'));
const base='http://127.0.0.1:8766';
const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
let browser;
(async()=>{
 browser=await chromium.launch({channel:'msedge',headless:true});
 const context=await browser.newContext({viewport:{width:1920,height:1080},recordVideo:{dir:out,size:{width:1920,height:1080}},locale:'zh-CN'});
 const page=await context.newPage();page.setDefaultTimeout(60000);page.on('dialog',dialog=>dialog.accept());
 await page.addInitScript(()=>document.addEventListener('DOMContentLoaded',()=>{
   const badge=document.createElement('div');badge.textContent='模拟数据 · 离线演示 · 合成普通话旁白';
   badge.style.cssText='position:fixed;bottom:12px;left:16px;z-index:9999;background:#123d31;color:white;padding:8px 14px;border-radius:5px;font:16px sans-serif;pointer-events:none';
   document.body.append(badge);
 }));
 const marks=[];
 async function chapter(i,action){
   const start=Date.now();marks.push({chapter:i,start});console.log('chapter '+(i+1));
   await action();const elapsed=Date.now()-start;
   if(elapsed>timings[i]*1000) throw Error('Chapter actions exceed narration window '+i);
   await wait(timings[i]*1000-elapsed);
 }
 let id;
 await chapter(0,async()=>{await page.goto(base);await page.getByRole('heading',{name:'让下一次面试，更有把握'}).waitFor();});
 await chapter(1,async()=>{
   await page.getByRole('link',{name:'简历档案',exact:true}).click();await wait(2000);
   await page.getByRole('button',{name:'使用示例简历',exact:true}).click();await wait(3000);
   await page.getByRole('button',{name:'查看 / 编辑',exact:true}).click();await wait(8000);
   await page.getByRole('button',{name:'保存并重新解析',exact:true}).click();
 });
 await chapter(2,async()=>{
   const data=await (await page.request.get(base+'/api/bootstrap')).json();
   await page.goto(base+'/#/new?resume='+data.resumes[0].id);
   await page.getByLabel('目标岗位或面试方向').fill('后端开发实习生');
   await page.getByLabel('岗位描述 / 导师方向 （可选）').fill('需要 Python、MySQL，重视接口测试与问题定位。');await wait(6000);
   await page.getByRole('button',{name:'生成题目并开始',exact:true}).click();
   await page.getByLabel('你的回答',{exact:true}).waitFor();id=page.url().split('/').pop();
 });
 await chapter(3,async()=>{
   await page.getByLabel('你的回答',{exact:true}).fill('在校园设备监测项目中，我负责 Python 采集接口与异常日志。首先检查采集结果，因为可能出现重复写入，所以增加唯一标识。最终通过12个测试用例对照日志验证功能，确认重复记录不会再次出现。');await wait(6500);
   await page.getByRole('button',{name:/提交回答并追问/}).click();await page.getByLabel('补充回答',{exact:true}).waitFor();await wait(6000);
   await page.getByLabel('补充回答',{exact:true}).fill('我比较了先查询再写入和数据库唯一约束，最终通过并发测试验证唯一约束可以阻止重复写入。');
 });
 await chapter(4,async()=>{
   await page.getByRole('button',{name:/提交补充并评分/}).click();await page.getByRole('heading',{name:'本题练习反馈',exact:true}).waitFor();
   await page.getByRole('heading',{name:'本题练习反馈',exact:true}).scrollIntoViewIfNeeded();await wait(10000);
   await page.getByRole('button',{name:'STAR 回答整理',exact:true}).click();await page.locator('.star-text').scrollIntoViewIfNeeded();
 });
 await chapter(5,async()=>{
   await page.getByRole('button',{name:/继续下一题/}).click();
   for(let i=1;i<6;i++) {await page.getByRole('button',{name:/跳过本题/}).click();await wait(700);}
   await page.getByRole('heading',{name:'练习报告',exact:true}).waitFor();await page.evaluate(()=>window.scrollTo(0,0));await wait(5000);
   const [download]=await Promise.all([page.waitForEvent('download'),page.getByRole('link',{name:'导出 Markdown',exact:true}).click()]);
   await download.saveAs(path.join(out,'demo-report.md'));
 });
 await chapter(6,async()=>{await page.getByRole('link',{name:'模型设置',exact:true}).click();await wait(8000);await page.evaluate(()=>window.scrollTo(0,350));});
 await chapter(7,async()=>{await page.getByRole('link',{name:'练习总览',exact:true}).click();await page.evaluate(()=>window.scrollTo(0,0));});
 const video=page.video();await context.close();await video.saveAs(path.join(out,'screen.webm'));await browser.close();
 fs.writeFileSync(path.join(out,'recording.json'),JSON.stringify({marks,duration_seconds:timings.reduce((a,b)=>a+b,0),mode:'offline',synthetic_data:true,synthetic_narration:true,session_id:id},null,2));
})().catch(async error=>{console.error(error);await browser?.close();process.exitCode=1;});
