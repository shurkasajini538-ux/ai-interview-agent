'use strict';
const state = {data:null, session:null, busy:false, busyText:'', error:'', tab:'feedback', search:'', testResult:'',setupDraft:null};
const icons = {
  home:'<path d="m3 10 9-7 9 7v10H3Z"/><path d="M9 20v-7h6v7"/>',
  file:'<path d="M6 3h8l4 4v14H6Z"/><path d="M14 3v5h4M9 12h6M9 16h6"/>',
  chat:'<path d="M3 4h18v13H9l-5 4v-4H3Z"/><path d="M7 9h10M7 12h7"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  settings:'<path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z"/><path d="m9 3-1 3-3 1-2 3 2 2-1 4 3 2 3-1 2 3 3-1 1-3 3-1 2-3-2-2 1-4-3-2-3 1-2-3Z"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 15v6h16v-6"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  spark:'<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5Z"/>',
  chart:'<path d="M4 3v18h17M8 16v-5m5 5V7m5 9V4"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V6a4 4 0 0 1 8 0v4M12 14v3"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 10v7M12 6v1"/>',
  close:'<path d="m6 6 12 12M18 6 6 18"/>',
  download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',
  edit:'<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14Z"/>',
  target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
  trash:'<path d="M4 6h16M9 6V3h6v3M6 6l1 15h10l1-15M10 10v7m4-7v7"/>',
};
const icon = key => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${icons[key]||icons.file}</svg>`;
const esc = value => String(value??'').replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const date = value => new Date(value).toLocaleDateString('zh-CN',{month:'2-digit',day:'2-digit'});
const fullDate = value => new Date(value).toLocaleString('zh-CN',{hour12:false});
const tag = (text, type='')=>`<span class="tag ${type}">${esc(text)}</span>`;
const btn = (label, action, cls='', extra='')=>`<button class="btn ${cls}" data-action="${action}" ${extra} ${state.busy?'disabled':''}>${label}</button>`;
const link = (label, url, cls='')=>`<a class="btn ${cls}" href="${esc(url)}">${label}</a>`;
const note = (text, cls='')=>`<div class="callout ${cls}">${icon('info')}<span>${esc(text)}</span></div>`;
const engineName = engine => ({online:'在线模型',local:'离线规则',local_fallback:'离线规则 · 在线回退'}[engine]||'离线规则');
const empty = (title, text, action='')=>`<div class="empty"><div class="empty-icon">${icon('file')}</div><h3>${esc(title)}</h3><p>${esc(text)}</p>${action}</div>`;
function route(){ const raw=(location.hash||'#/overview').slice(2); const [path,query='']=raw.split('?'); return {parts:path.split('/'),query:new URLSearchParams(query)}; }
function toast(text,error=false){const node=document.querySelector('#toast');node.textContent=text;node.className='show'+(error?' error':'');clearTimeout(toast.timer);toast.timer=setTimeout(()=>node.className='',5000);}
async function api(path, body){
  const response=await fetch(path,body===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Studio-Request':'1'},body:JSON.stringify(body)});
  const data=await response.json();if(!response.ok)throw Error(data.error||'请求失败，请重试。');return data;
}
function navigate(path){if(location.hash==='#/'+path)loadRoute();else location.hash='/'+path;}
function busy(text){state.busy=true;state.busyText=text;state.error='';render();}
function pageHeader(eyebrow,title,subtitle,actions=''){return `<div class="page-header"><div><div class="eyebrow">${esc(eyebrow)}</div><h1>${esc(title)}</h1><p>${esc(subtitle)}</p></div><div class="button-row">${actions}</div></div>`;}
function busyNotice(){return state.busy?`<div class="callout"><span class="spinner"></span><span>${esc(state.busyText)}${state.data?.settings.mode==='online'?' · 模型处理可能需要约一分钟，请稍候。':''}</span></div><div class="spacer"></div>`:'';}
function render(){
  if(!state.data)return;
  const r=route(), active=r.parts[0], nav=[['overview','home','练习总览'],['resumes','file','简历档案'],['new','chat','开始练习'],['history','clock','练习记录'],['settings','settings','模型设置']];
  const settings=state.data.settings;
  const names={overview:'练习总览',resumes:'简历档案',new:'开始练习',history:'练习记录',settings:'模型设置',interview:'模拟面试',report:'练习报告'};
  const body={overview:overview,resumes:resumesPage,new:setupPage,history:historyPage,settings:settingsPage,interview:interviewPage,report:reportPage}[active]||overview;
  document.querySelector('#app').innerHTML=`<div class="shell"><aside class="sidebar"><a href="#/overview" class="brand"><img src="/assets/icon.svg" alt=""><div><strong>面试工坊</strong><small>INTERVIEW STUDIO</small></div></a><div class="nav-label">我的练习空间</div><nav>${nav.map(([path,key,label])=>`<a aria-label="${esc(label)}" class="nav-item ${active===path||(path==='new'&&active==='interview')?'active':''}" href="#/${path}">${icon(key)}<span>${label}</span>${path==='resumes'?`<span class="nav-count">${state.data.resumes.length}</span>`:''}</a>`).join('')}</nav><div class="sidebar-bottom"><div class="sidebar-card"><h3>每次练习，都有依据。</h3><p>从真实经历出发，逐题深入，把回答讲得更清楚。</p>${link('开始一轮练习 '+icon('arrow'),'#/new','small')}</div><div class="local-profile"><div class="avatar">练</div><div><span>我的本地空间</span><small>记录保存在这台电脑</small></div></div></div></aside><main class="main"><header class="topbar"><div class="breadcrumb">工作台 <b>/ ${esc(names[active]||'练习总览')}</b></div><div class="top-status"><span class="engine-chip"><i class="dot"></i>${settings.mode==='online'?'在线模型已选择':'离线练习模式'}</span><span class="date">${new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'long',day:'numeric',weekday:'short'})}</span></div></header><div class="content">${state.error?note(state.error,'error')+'<div class="spacer"></div>':''}${busyNotice()}${body()}<div class="footer-note">面试工坊 · 以真实经历为起点，让每一次练习留下进步</div></div></main></div>`;
  if(active==='new'){
    const form=document.querySelector('#setup-form');
    if(form&&state.setupDraft)for(const [key,val] of Object.entries(state.setupDraft)){if(form.elements[key])form.elements[key].value=val;}
    const selected=r.query.get('resume');if(selected&&document.querySelector('#setup-resume')&&!state.setupDraft)document.querySelector('#setup-resume').value=selected;
  }
  if(active==='interview')restoreDraft();
}
function overview(){
  const d=state.data, s=d.stats, active=d.sessions.find(x=>x.status==='active');
  const stats=[['简历档案',s.resumes,'份','已导入并保存在本机','file'],['练习次数',s.sessions,'次','包含进行中与已完成练习','chat'],['已评分回答',s.answered,'题','跳过题目不计入平均分','check'],['平均练习分',s.average??'—','/ 100','请结合评分依据理解分数','chart']];
  const history=d.sessions.filter(x=>x.average!==null).slice(0,8).reverse();
  return pageHeader('YOUR PRACTICE, IN FOCUS','让下一次面试，更有把握','整理经历，练习表达，回看每一步进展。',link(icon('plus')+' 新建练习','#/new','primary'))+
  `<section class="hero"><div><div class="eyebrow">从真实经历开始</div><h2>把经历讲清楚，<br>把准备变成底气。</h2><p>导入简历，针对目标岗位逐题练习。用追问补齐细节，用有依据的反馈改进下一次回答。</p><div class="button-row">${link('开始面试练习 '+icon('arrow'),'#/new','lime')}${active?link('继续上次练习',`#/interview/${active.id}`,'ghost hero-continue'):''}</div></div><div class="hero-art" aria-hidden="true"><div class="orbit"></div><div class="art-badge">真实经历 · 有据可循</div><div class="art-card"><b>我的面试准备</b><div class="art-line"></div><div class="art-line short"></div><div class="art-line"></div><div class="tag-row">${tag('项目经历')}${tag('个人贡献')}</div><div class="art-line"></div></div><div class="art-score"><small>练习的每一步</small><strong>都有进步 ↗</strong><small>回答 · 追问 · 反馈</small></div></div></section>`+
  `<div class="stat-grid">${stats.map(([label,val,unit,foot,key])=>`<div class="stat-card"><div class="stat-icon">${icon(key)}</div><div class="stat-label">${label}</div><div class="stat-value">${esc(val)}<small>${unit}</small></div><div class="stat-foot">${foot}</div></div>`).join('')}</div>`+
  `<div class="two-col"><section class="panel"><div class="panel-head"><div><h2>最近练习</h2><p>保存每次回答，随时回到上次的位置。</p></div>${link('查看全部 '+icon('arrow'),'#/history','ghost small')}</div>${d.sessions.length?d.sessions.slice(0,4).map(sessionRow).join(''):empty('还没有练习记录','先导入一份简历，再开始你的第一轮面试。',link('导入简历','#/resumes','small'))}</section><section class="panel"><div class="panel-head"><div><h2>能力观察</h2><p>已评分回答的分项均值 · 每项 25 分</p></div>${icon('target')}</div>${Object.keys(s.dimensions).length?bars(s.dimensions,25):empty('等待你的第一份反馈','完成回答后，这里会展示结构、深度、表达和证据表现。')}</section></div><div class="spacer"></div>`+
  `<div class="two-col"><section class="panel"><div class="panel-head"><div><h2>练习轨迹</h2><p>最近 ${history.length} 次有评分的练习</p></div>${tag('按时间排序','gray')}</div>${history.length?`<div class="trend-wrap"><div class="mini-trend">${history.map(h=>`<div class="trend-column" style="height:${Math.max(3,h.average)}%"><span>${h.average}</span><small>${date(h.created_at)}</small></div>`).join('')}</div></div><p class="section-note">不同模型与模式的评分标准可能不同；建议在相同设置下对照练习。</p>`:empty('进步会在这里留下轨迹','完成练习后，回来看看你在哪些地方讲得更好了。')}</section><section class="panel"><div class="panel-head"><div><h2>下一次，重点练什么</h2><p>根据近期分项表现生成</p></div></div>${d.weak_points.length?d.weak_points.map((w,i)=>`<div class="step mt"><div class="step-number">${i+1}</div><div><b>${esc(w.label)}</b><p>近期对应维度均分 ${w.average}/25，下一轮将提示关注。</p></div></div>`).join(''):empty('先建立你的练习基线','有了实际回答，才有适合你的改进建议。')}</section></div>`;
}
function bars(values,max){return `<div class="bars">${Object.entries(values).map(([label,value])=>`<div><div class="bar-top"><span>${esc(label)}</span><span>${esc(value)}${max===25?' / 25':''}</span></div><div class="bar-track"><div class="bar-fill" style="width:${Math.min(100,value/max*100)}%"></div></div></div>`).join('')}</div>`;}
function sessionRow(s){return `<div class="list-row"><div class="file-icon">${icon('chat')}</div><div class="row-main"><b>${esc(s.role)}</b><small>${esc(s.resume_name)} · ${date(s.created_at)} · 已评分 ${s.answered}/${s.question_count}</small></div>${s.average!==null?`<span class="score-pill">${s.average} 分</span>`:''}${link(s.status==='completed'?'查看报告':'继续练习',`#/${s.status==='completed'?'report':'interview'}/${s.id}`,'small')}</div>`;}
function resumesPage(){
  const d=state.data, filtered=d.resumes.filter(r=>(r.title+' '+r.parsed.skills.join(' ')).toLowerCase().includes(state.search.toLowerCase()));
  return pageHeader('RESUME LIBRARY','从你的经历，找到练习起点','支持文字、Word、PDF 与图片；所有解析结果都可以核对修改。',btn(icon('plus')+' 导入简历','import','primary'))+
  `<div class="library-controls"><input id="resume-search" placeholder="搜索简历名称或技能…" aria-label="搜索简历" value="${esc(state.search)}">${btn('使用示例简历','sample','')}</div>`+
  (filtered.length?`<div class="library-grid">${filtered.map(r=>`<article class="resume-card"><div class="button-row"><div class="file-icon">${icon('file')}</div>${tag(r.parsed.education||'学历未提供','gray')}</div><h3>${esc(r.title)}</h3><p>${date(r.created_at)} 导入 · ${r.parsed.character_count.toLocaleString()} 字 · ${r.parsed.projects.length} 段识别项目</p><div class="tag-row">${r.parsed.skills.slice(0,5).map(s=>tag(s)).join('')||tag('请核对简历内容','gray')}</div><div class="button-row">${link('开始练习',`#/new?resume=${r.id}`,'primary small')}${btn('查看 / 编辑','edit-resume','small',`data-id="${r.id}"`)}${btn(icon('trash'),'delete-resume','ghost small',`data-id="${r.id}" aria-label="删除简历"`)}</div></article>`).join('')}</div>`:empty(state.search?'没有匹配的简历':'你的简历档案还是空的',state.search?'换个关键词试试。':'可以先使用示例体验，再导入自己的真实简历。',btn('导入第一份简历','import','primary')))+
  (d.resumes.length?`<div class="stats-summary"><section class="panel"><div class="panel-head"><div><h2>档案中的技能</h2><p>按实际简历中出现的次数统计</p></div></div>${Object.keys(d.stats.skills).length?bars(d.stats.skills,Math.max(...Object.values(d.stats.skills))):'<p class="section-note">尚未识别到技能关键词，可在简历中补充。</p>'}</section><section class="panel"><div class="panel-head"><div><h2>学历分布</h2><p>仅显示明确提供的学历，缺失值保持未知</p></div></div>${bars(d.stats.education,d.resumes.length)}<div class="spacer"></div>${note('批量导入后，统计直接来自已保存的简历内容。系统不推断薪资、工作年限或招聘优先级。')}</section></div>`:'');
}
function setupPage(){
  const d=state.data;
  return pageHeader('A PRACTICE THAT FITS YOU','准备好，开始这一轮','选择简历与目标岗位，生成本次固定题目。',link('管理简历','#/resumes',''))+
  `<div class="setup-layout"><section class="panel"><div class="panel-head"><h2>练习设置</h2>${tag(d.settings.mode==='online'?'在线模型':'离线规则',d.settings.mode==='online'?'online':'gray')}</div>${d.resumes.length?`<form id="setup-form"><div class="form-field"><label for="setup-resume">本次使用的简历</label><select id="setup-resume" name="resume_id">${d.resumes.map(r=>`<option value="${r.id}">${esc(r.title)} · ${date(r.updated_at)} 更新</option>`).join('')}</select></div><div class="form-field"><label for="setup-role">目标岗位或面试方向</label><input id="setup-role" name="role" placeholder="例如：后端开发实习生 / 计算机保研" required maxlength="100" value="后端开发实习生"><div class="role-chips">${['后端开发实习生','前端开发实习生','数据分析师','产品经理','计算机保研'].map(role=>`<button type="button" class="role-chip" data-action="choose-role" data-role="${role}">${role}</button>`).join('')}</div></div><div class="form-inline"><div class="form-field"><label for="setup-count">本轮题数</label><select id="setup-count" name="count"><option value="6">6 题 · 约 15 分钟</option><option value="8">8 题 · 约 20 分钟</option><option value="10">10 题 · 约 25 分钟</option></select></div><div class="form-field"><label for="setup-difficulty">追问深度</label><select id="setup-difficulty" name="difficulty"><option>标准</option><option>入门引导</option><option>深入挑战</option></select></div></div><div class="form-field"><label for="setup-jd">岗位描述 / 导师方向 <span class="text-muted">（可选）</span></label><textarea id="setup-jd" name="job_description" maxlength="6000" placeholder="粘贴岗位职责与要求，帮助问题更贴合目标。"></textarea></div>${d.settings.mode==='online'?note('开始后，简历内容和岗位描述会发送至你配置的模型服务；联系方式默认自动隐藏。'):note('离线模式根据简历中的项目、技能和已有薄弱点出题。深入语义反馈可在模型设置中启用在线模型。')}<div class="spacer"></div><button type="submit" class="btn primary" ${state.busy?'disabled':''}>${icon('spark')} 生成题目并开始</button></form>`:empty('先准备一份简历','导入后就能开始练习，也可以使用示例简历。',link('去导入简历','#/resumes','primary'))}</section><aside class="panel"><div class="panel-head"><h2>这一轮，你会经历</h2></div><div class="steps">${[['针对性提问','根据简历、岗位与近期薄弱点准备题目。'],['回答与追问','每题先回答，再通过一道追问补齐关键细节。'],['查看有依据的反馈','四项评分、回答证据，以及下一步改进。'],['整理与重新练习','按 STAR 组织真实事实，可重答当前题。'],['保存你的练习报告','历史自动保存，支持导出与打印。']].map(([a,b],i)=>`<div class="step"><div class="step-number">${i+1}</div><div><b>${a}</b><p>${b}</p></div></div>`).join('')}</div><div class="spacer"></div>${d.weak_points.length?note('本次将关注：'+d.weak_points.map(w=>w.label).join('；')):note('建议准备一个真实项目、一次问题解决经历，以及能够核对的成果证据。')}</aside></div>`;
}
function currentQuestion(){return state.session?.questions[state.session.current_index];}
function draftKey(){const q=currentQuestion();return q?`studio:draft:${state.session.id}:${q.id}:${q.stage}`:'';}
function restoreDraft(){const textarea=document.querySelector('#answer-text');if(textarea){try{textarea.value=localStorage.getItem(draftKey())||'';}catch{}updateCount();}}
function updateCount(){const node=document.querySelector('#answer-count');if(node)node.textContent=`${document.querySelector('#answer-text')?.value.length||0} / 10,000 字 · 草稿保存在此浏览器`;}
function questionEvidence(q){return `<details class="evidence-box"><summary>简历依据与考察要点</summary><pre>${esc(q.source)}</pre><div class="spacer"></div><b>考察要点：</b>${esc(q.objective)}</details>`;}
function interviewPage(){
  const s=state.session;if(!s)return empty('正在读取练习','请稍候。');
  if(s.status==='completed')return reportPage();
  const q=currentQuestion(), done=s.questions.filter(x=>x.result||x.stage==='skipped').length;
  return pageHeader('IN THE INTERVIEW',s.role,`${s.resume_name} · 练习随进度自动保存`,link('查看当前报告',`#/report/${s.id}`,'')+link('返回记录','#/history','ghost'))+
  `<div class="interview-layout"><aside class="panel question-rail"><div class="rail-title">本轮题目 · ${s.questions.length} 题</div>${s.questions.map((x,i)=>`<div class="rail-item ${i===s.current_index?'current':''} ${x.result?'done':''}"><span class="num">${x.result?'✓':x.stage==='skipped'?'–':i+1}</span><div><b>${esc(x.category)}</b><small>${x.result?x.result.total+' / 100':x.stage==='skipped'?'已跳过':i===s.current_index?'正在练习':'等待作答'}</small></div></div>`).join('')}<div class="rail-summary"><div class="bar-top"><span>本轮进度</span><span>${done}/${s.questions.length}</span></div><div class="progress-track"><div style="width:${done/s.questions.length*100}%"></div></div><p class="section-note">${esc(engineName(s.engine))}${s.model?' · '+esc(s.model):''}</p>${s.memory_used.length?`<p class="section-note mt">本次关注：${esc(s.memory_used[0].label)}</p>`:''}</div></aside><section class="panel"><div class="question-header"><h2>第 ${s.current_index+1} 题 / ${s.questions.length}</h2>${tag(q.category)}</div>${s.notice?note(s.notice,'warn')+'<div class="spacer"></div>':''}<div class="chat-label">${icon('chat')} 面试官</div><div class="question-bubble">${esc(q.text)}</div>${questionEvidence(q)}${q.answers.map((a,i)=>`<div class="answer-bubble"><div class="chat-label">你的${i?'补充':'回答'}</div>${esc(a.text)}</div>${i===0&&q.followup?`<div class="followup-bubble"><div class="chat-label">${icon('chat')} 深入追问 · ${esc(engineName(q.followup_engine))}</div>${esc(q.followup)}</div>`:''}`).join('')}${q.notice&&q.stage==='followup'?note(q.notice,'warn'):''}${q.result?resultView(q.result):answerComposer(q)}${q.result?`<div class="compose-footer mt"><span class="section-note">${q.attempts.length?'已保留 '+q.attempts.length+' 次历史作答。':'可以重新作答本题，已有反馈会保留。'}</span><div class="button-row">${btn('重新作答本题','retry','')}${btn(s.current_index===s.questions.length-1?'完成并查看报告 '+icon('check'):'继续下一题 '+icon('arrow'),'next','primary')}</div></div>`:''}</section></div>`;
}
function answerComposer(q){return `<div class="answer-compose"><form id="answer-form"><div class="form-field"><label for="answer-text">${q.stage==='followup'?'补充回答':'你的回答'}</label><textarea id="answer-text" name="answer" maxlength="10000" placeholder="${q.stage==='followup'?'针对追问补充真实细节。如果暂时没有更多信息，也可以直接评分。':'建议交代背景、你的任务、实际行动与结果。没有统计数字时，说明验证方法。'}" ${state.busy?'disabled':''}></textarea></div><div class="compose-footer"><small id="answer-count"></small><div class="button-row">${btn('跳过本题','skip','ghost')}${q.stage==='followup'?btn('以现有回答评分','evaluate-now',''):''}<button type="submit" class="btn primary" ${state.busy?'disabled':''}>${q.stage==='followup'?'提交补充并评分':'提交回答并追问'} ${icon('arrow')}</button></div></div></form></div>`;}
function resultView(r,report=false){
  const feedback=`<div>${r.dimensions.map(d=>`<div class="feedback-detail"><b>${esc(d.label)} · ${d.score}/25</b><p>${esc(d.feedback)}</p><blockquote>${d.evidence?'回答依据：“'+esc(d.evidence)+'”':'未引用直接回答证据，请结合建议核对。'}</blockquote></div>`).join('')}<h3 class="mt">下次先改进</h3><ul class="tips">${r.suggestions.map(s=>`<li>${esc(s)}</li>`).join('')}</ul></div>`;
  const star=`<div class="star-text">${esc(r.optimized)}</div><div class="spacer"></div>${r.missing_facts.length?note('待补充：'+r.missing_facts.join('；')):note('以上内容来自你的回答。建议核对后练习用自己的语言自然表达。')}${btn('复制整理结果','copy-star','small mt')}`;
  const details=report?feedback+`<h3 class="mt">STAR 整理 · 只使用已提供的事实</h3><div class="star-text mt">${esc(r.optimized)}</div>`:
    `<div class="tabs"><button class="tab ${state.tab==='feedback'?'active':''}" data-action="tab" data-tab="feedback">评分依据与改进</button><button class="tab ${state.tab==='star'?'active':''}" data-action="tab" data-tab="star">STAR 回答整理</button></div>`+(state.tab==='feedback'?feedback:star);
  return `<div class="result-score"><div class="score-number">${r.total}<small>/ 100</small></div><div><h3>本题练习反馈</h3><p>${esc(engineName(r.engine))} · 总分由四项分数相加</p></div></div><div class="dimension-grid">${r.dimensions.map(d=>`<div class="dimension"><span>${esc(d.label)}</span><b>${d.score}</b><small> /25</small></div>`).join('')}</div>${note(r.notice,r.engine==='local_fallback'?'warn':'')}${details}`;
}
function historyPage(){
  const sessions=state.data.sessions;
  return pageHeader('YOUR PRACTICE JOURNAL','每一次练习，都能回看','继续未完成的练习，或查看回答、反馈与报告。',link(icon('plus')+' 新建练习','#/new','primary'))+
  `<section class="panel">${sessions.length?`<div class="table-wrap"><table><thead><tr><th>目标岗位</th><th>简历 / 时间</th><th>进度</th><th>平均分</th><th>状态</th><th>操作</th></tr></thead><tbody>${sessions.map(s=>`<tr><td>${esc(s.role)}</td><td>${esc(s.resume_name)}<br><span class="text-muted">${fullDate(s.created_at)}</span></td><td>${s.answered} 已评分 / ${s.question_count} 题${s.skipped?'<br>'+s.skipped+' 已跳过':''}</td><td>${s.average??'—'}</td><td>${tag(s.status==='completed'?'已完成':'进行中',s.status==='completed'?'':'gray')}</td><td><div class="button-row">${link(s.status==='completed'?'报告':'继续',`#/${s.status==='completed'?'report':'interview'}/${s.id}`,'small')}${s.status!=='completed'?link('报告',`#/report/${s.id}`,'ghost small'):''}${btn(icon('trash'),'delete-session','ghost small',`data-id="${s.id}" aria-label="删除练习"`)}</div></td></tr>`).join('')}</tbody></table></div>`:empty('还没有练习记录','从一份简历开始，建立你的第一份练习档案。',link('开始练习','#/new','primary'))}</section>`;
}
function reportPage(){
  const s=state.session;if(!s)return empty('正在读取报告','请稍候。');
  const results=s.questions.filter(q=>q.result).map(q=>q.result), avg=results.length?Math.round(results.reduce((n,r)=>n+r.total,0)/results.length*10)/10:null;
  return pageHeader('A RECORD OF YOUR PROGRESS','练习报告',`${s.resume_name} · ${fullDate(s.created_at)}`,`${s.status==='active'?link('继续练习',`#/interview/${s.id}`,'primary'):''}<a class="btn" href="/api/sessions/${s.id}/export?format=md">${icon('download')} 导出 Markdown</a><a class="btn" href="/api/sessions/${s.id}/export?format=json">JSON</a>${btn('打印 / 保存 PDF','print','')}`)+
  `<div class="report-head"><div><div class="eyebrow">${s.status==='completed'?'本轮练习已完成':'本轮练习进行中'}</div><h2>${esc(s.role)}</h2><p>已评分 ${results.length}/${s.questions.length} 题 · ${esc(engineName(s.engine))}${s.model?' · '+esc(s.model):''}</p></div><div class="report-total">${avg??'—'}<small> / 100</small></div></div>${note('平均分仅包含已评分题目。不同模型或模式的分数不可直接等同；请优先查看回答依据与具体改进。')}<div class="spacer"></div><section class="panel"><div class="panel-head"><h2>下一轮练习计划</h2></div><div class="steps">${['补齐 STAR 整理中标记的待确认事实，准备可以核对的测试、反馈或产出。','选择本轮得分较低的维度，重写回答后请教师或同伴核对。','在相近岗位、相同模型与评分模式下重新练习，比较内容和表达的变化。'].map((t,i)=>`<div class="step"><div class="step-number">${i+1}</div><div class="text-small">${t}</div></div>`).join('')}</div></section>${s.questions.map((q,i)=>`<details class="panel report-question" ${q.result?'open':''}><summary><span>第 ${i+1} 题 · ${esc(q.category)}</span><span class="score-pill">${q.result?q.result.total+' / 100':q.stage==='skipped'?'已跳过':'尚未评分'}</span></summary><div><div class="question-bubble">${esc(q.text)}</div>${questionEvidence(q)}${q.answers.map((a,j)=>`<div class="answer-bubble"><div class="chat-label">${j?'补充':'首次'}回答</div>${esc(a.text)}</div>`).join('')}${q.followup?`<div class="followup-bubble">追问：${esc(q.followup)}</div>`:''}${q.result?resultView(q.result,true):'<p class="section-note">本题尚无评分，不计入平均分。</p>'}${q.attempts.length?`<details class="evidence-box"><summary>查看此前 ${q.attempts.length} 次作答</summary>${q.attempts.map((a,j)=>`<div class="feedback-detail"><b>第 ${j+1} 次 · ${a.result.total}/100</b><pre>${esc(a.answers.map(x=>x.text).join('\n'))}</pre></div>`).join('')}</details>`:''}</div></details>`).join('')}`;
}
function settingsPage(){
  const s=state.data.settings;
  return pageHeader('YOUR MODEL, YOUR CHOICE','选择适合你的练习方式','在线模型提供语义反馈；离线模式可以随时练习。')+
  `<div class="settings-layout"><section class="panel"><form id="settings-form"><div class="select-mode"><label class="mode-choice"><input type="radio" name="mode" value="online" ${s.mode==='online'?'checked':''}><span><b>在线模型</b><small>更细致的个性化问题与反馈</small></span></label><label class="mode-choice"><input type="radio" name="mode" value="local" ${s.mode==='local'?'checked':''}><span><b>离线练习</b><small>本机规则辅助，无模型调用</small></span></label></div><div class="form-field"><label for="model-base">OpenAI 兼容接口地址</label><input id="model-base" name="base_url" value="${esc(s.base_url)}" placeholder="https://api.deepseek.com/v1" required><small>填写服务商的 API 基础地址。本机模型也可使用 localhost。</small></div><div class="form-field"><label for="model-name">模型名称</label><input id="model-name" name="model" value="${esc(s.model)}" required placeholder="deepseek-chat"></div><div class="form-field"><label for="model-key">API Key ${s.has_key?tag('已配置','online'):tag('未配置','gray')}</label><input id="model-key" name="api_key" type="password" autocomplete="new-password" placeholder="${s.has_key?'留空保留当前密钥；填写新值会替换':'填写你的 API Key'}"><small>密钥不会回传到浏览器。存储方式：${esc(s.key_storage)}。</small></div><label class="checkbox-row"><input type="checkbox" name="redact_contacts" ${s.redact_contacts?'checked':''}>发送给模型前隐藏手机号、邮箱和身份证号</label><div class="spacer"></div><div class="button-row"><button type="submit" class="btn primary" ${state.busy?'disabled':''}>保存设置</button>${btn('保存并测试连接','test-model','')}${s.has_key?btn('清除密钥','clear-key','ghost danger'):''}</div></form>${state.testResult?`<div class="spacer"></div>${note(state.testResult)}`:''}</section><aside class="panel"><div class="settings-note"><h3>沿用你已有的模型</h3>新应用支持 OpenAI 兼容的聊天接口。你原有项目的有效配置可以直接用于这里；是否可用以连接测试结果为准。</div><div class="settings-note"><h3>数据存在哪里</h3>简历、回答与报告保存在本机 SQLite 数据库。不同浏览器空间分别保存记录；请固定使用一个浏览器，并定期导出重要报告。</div><div class="settings-note"><h3>哪些内容会发送出去</h3>仅在在线模式下，相关简历内容、岗位要求与回答会发送到你填写的模型服务。文件解析与图片 OCR 在本机完成。</div><div class="settings-note"><h3>反馈应该如何使用</h3>模型评分和离线规则评分都用于练习参考。系统会展示具体依据，并保留缺失事实，建议结合教师反馈核对技术内容。</div></aside></div>`;
}
function importDialog(){
  document.querySelector('#modal-root').innerHTML=`<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="import-title"><div class="modal-head"><div><div class="eyebrow">BRING YOUR EXPERIENCE</div><h2 id="import-title">导入你的简历</h2></div>${btn(icon('close'),'close-modal','ghost', 'aria-label="关闭"')}</div><div class="form-field"><label for="resume-title">简历名称 <span class="text-muted">（可选）</span></label><input id="resume-title" placeholder="例如：后端实习 · 秋招版" maxlength="100"></div><label class="drop-zone" id="drop-zone">${icon('upload')}<strong>拖入文件，或点击选择</strong><span>PDF / DOCX / PNG / JPG / WEBP / TXT / MD</span><span>每份不超过 12 MB · 一次最多 5 份 · 图片在本机识别</span><input type="file" id="resume-files" multiple accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.bmp,.txt,.md"></label><div id="upload-status" class="upload-status" role="status"></div><div class="divider">或者粘贴文字</div><div class="form-field"><textarea id="resume-paste" placeholder="粘贴简历正文。可以保留原有项目标题、技能与教育信息。" style="min-height:180px"></textarea></div><div class="button-row">${btn('保存文字简历','save-paste','primary')}${btn('使用示例简历','sample','')}</div><div class="spacer"></div>${note('导入后可以核对与修改全文。无法确认的学历和信息会保持未知，不会自动补造。')}</section></div>`;
  document.querySelector('#resume-title').focus();
}
async function editResume(id){
  const r=await api('/api/resumes/'+id);
  document.querySelector('#modal-root').innerHTML=`<div class="modal-backdrop"><section class="modal" role="dialog" aria-modal="true" aria-labelledby="edit-title"><div class="modal-head"><div><div class="eyebrow">CHECK THE FACTS</div><h2 id="edit-title">核对简历内容</h2></div>${btn(icon('close'),'close-modal','ghost','aria-label="关闭"')}</div><form id="edit-resume-form" data-id="${id}"><div class="form-field"><label for="edit-name">名称</label><input id="edit-name" name="title" value="${esc(r.title)}" maxlength="100" required></div><div class="detail-facts"><div class="detail-fact"><span>识别姓名</span><b>${esc(r.parsed.name||'未明确提供')}</b></div><div class="detail-fact"><span>明确学历</span><b>${esc(r.parsed.education||'未明确提供')}</b></div></div><div class="tag-row">${r.parsed.skills.map(s=>tag(s)).join('')}</div><div class="spacer"></div>${r.warnings.map(w=>note(w,'warn')).join('')}<div class="form-field mt"><label for="edit-text">可编辑全文</label><textarea id="edit-text" name="text" maxlength="60000">${esc(r.text)}</textarea><small>保存后会重新解析。已有练习保留当时的简历快照。</small></div><div class="button-row"><button type="submit" class="btn primary">保存并重新解析</button>${btn('关闭','close-modal','')}</div></form></section></div>`;
}
async function refresh(){state.data=await api('/api/bootstrap');}
async function loadRoute(){
  try{
    document.querySelector('#modal-root').innerHTML='';state.error='';state.tab='feedback';
    const r=route();
    if(['interview','report'].includes(r.parts[0])&&r.parts[1])state.session=await api('/api/sessions/'+r.parts[1]);
    else state.session=null;
    await refresh();render();window.scrollTo(0,0);
  }catch(e){state.error=e.message;if(state.data)render();else document.querySelector('#app').innerHTML=empty('应用暂时无法连接','请确认启动程序仍在运行，然后刷新页面。');}
}
function requestId(){return window.crypto?.randomUUID?crypto.randomUUID():Date.now()+'-'+Math.random().toString(36).slice(2);}
async function sessionAction(action,answer='',evaluateNow=false){
  if(state.busy)return;
  const q=currentQuestion(), key=draftKey(), sessionId=state.session.id;
  busy(action==='answer'?(evaluateNow||q.stage==='followup'?'正在分析回答、整理评分依据':'正在根据回答准备追问'):'正在保存练习进度');
  try{
    state.session=await api(`/api/sessions/${sessionId}/${action}`,{question_id:q.id,answer,evaluate_now:evaluateNow,request_id:requestId()});
    if(action==='answer')try{localStorage.removeItem(key);}catch{}
    state.tab='feedback';await refresh();state.busy=false;
    if(state.session.status==='completed')navigate('report/'+sessionId);else render();
  }catch(e){state.busy=false;state.error=e.message;render();toast(e.message,true);}
}
async function importFiles(files){
  if(state.busy)return;const chosen=[...files];if(chosen.length>5)return toast('一次最多导入 5 份简历。',true);
  state.busy=true;const title=document.querySelector('#resume-title')?.value||'';let count=0;const errors=[];
  const controls=document.querySelectorAll('.modal button,.modal input,.modal textarea');controls.forEach(x=>x.disabled=true);
  for(let i=0;i<chosen.length;i++){
    const f=chosen[i], status=document.querySelector('#upload-status');if(status)status.innerHTML=`<span class="spinner"></span> 正在解析 ${i+1}/${chosen.length}：${esc(f.name)}，首次图片识别可能需要一些时间…`;
    try{
      if(f.size>12*1024*1024)throw Error('文件超过 12 MB');
      const data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(Error('文件读取失败'));reader.readAsDataURL(f);});
      await api('/api/resumes',{filename:f.name,file_data:data,title:chosen.length===1?title:''});count++;
    }catch(e){errors.push(f.name+'：'+e.message);}
  }
  state.busy=false;await refresh();render();
  if(errors.length){controls.forEach(x=>x.disabled=false);const n=document.querySelector('#upload-status');if(n)n.textContent=`已成功 ${count} 份。`+errors.join('；');toast(`已导入 ${count} 份，${errors.length} 份需重试。`,true);}
  else{document.querySelector('#modal-root').innerHTML='';navigate('resumes');toast(`已导入 ${count} 份简历，请核对解析内容。`);}
}
async function saveSettings(test=false,clear=false){
  const form=document.querySelector('#settings-form');if(!form.reportValidity()||state.busy)return;
  const f=new FormData(form), payload={mode:f.get('mode'),base_url:f.get('base_url'),model:f.get('model'),api_key:f.get('api_key'),redact_contacts:f.get('redact_contacts')==='on',clear_key:clear};
  if(clear)payload.mode='local';
  busy(test?'正在测试模型连接':'正在保存设置');
  try{state.data.settings=await api('/api/settings',payload);state.testResult='';if(test){const r=await api('/api/settings/test',{});state.testResult=r.message;}state.busy=false;render();toast(test?'模型连接成功':'设置已保存');}
  catch(e){state.busy=false;state.error=e.message;render();toast(e.message,true);}
}
document.addEventListener('click',async event=>{
  if(state.busy&&event.target.closest('a[href^="#/"]')){event.preventDefault();toast('当前操作正在保存，请稍候。');return;}
  const node=event.target.closest('[data-action]');if(!node)return;const action=node.dataset.action;
  try{
    if(action==='close-modal'){if(!state.busy)document.querySelector('#modal-root').innerHTML='';return;}
    if(state.busy)return;
    if(action==='import')return importDialog();
    if(action==='edit-resume')return await editResume(node.dataset.id);
    if(action==='choose-role'){document.querySelector('#setup-role').value=node.dataset.role;return;}
    if(action==='tab'){state.tab=node.dataset.tab;render();return;}
    if(action==='print'){document.querySelectorAll('.report-question').forEach(x=>x.open=true);window.print();return;}
    if(action==='copy-star'){await navigator.clipboard.writeText(currentQuestion().result.optimized);toast('已复制 STAR 整理结果');return;}
    if(action==='sample'){
      const s=await api('/api/sample');await api('/api/resumes',{text:s.text,title:'示例 · 后端实习简历',filename:'示例简历.md'});
      document.querySelector('#modal-root').innerHTML='';await refresh();navigate('resumes');toast('已导入示例简历，内容为模拟数据。');return;
    }
    if(action==='save-paste'){
      const text=document.querySelector('#resume-paste').value,title=document.querySelector('#resume-title').value;
      if(text.trim().length<20)return toast('请至少输入 20 字简历内容。',true);
      node.disabled=true;await api('/api/resumes',{text,title});document.querySelector('#modal-root').innerHTML='';await refresh();navigate('resumes');toast('简历已保存');return;
    }
    if(action==='delete-resume'||action==='delete-session'){
      const type=action==='delete-resume'?'简历':'练习';
      if(!window.confirm(`确定删除这份${type}吗？${type==='简历'?'已有练习中的简历快照会保留。':'相关回答与反馈将一并删除。'}`))return;
      await api(`/api/${type==='简历'?'resumes':'sessions'}/${node.dataset.id}/delete`,{});await refresh();render();toast('已删除');return;
    }
    if(['next','retry','skip'].includes(action)){
      if(action==='skip'&&!window.confirm('确定跳过本题吗？跳过的题目不计入平均分。'))return;
      return await sessionAction(action);
    }
    if(action==='evaluate-now')return await sessionAction('answer',document.querySelector('#answer-text')?.value||'',true);
    if(action==='test-model')return await saveSettings(true);
    if(action==='clear-key'){if(window.confirm('清除当前密钥并切换到离线模式？'))await saveSettings(false,true);return;}
  }catch(e){node.disabled=false;toast(e.message,true);}
});
document.addEventListener('submit',async event=>{
  event.preventDefault();if(state.busy)return;const form=event.target;
  if(form.id==='settings-form')return saveSettings();
  if(form.id==='answer-form')return sessionAction('answer',document.querySelector('#answer-text').value);
  if(form.id==='setup-form'){
    const f=new FormData(form),payload={resume_id:f.get('resume_id'),role:f.get('role'),count:Number(f.get('count')),difficulty:f.get('difficulty'),job_description:f.get('job_description')};
    state.setupDraft=payload;
    busy('正在根据简历与目标岗位生成本轮题目');
    try{const s=await api('/api/sessions',payload);state.busy=false;state.session=s;state.setupDraft=null;navigate('interview/'+s.id);}
    catch(e){state.busy=false;state.error=e.message;render();toast(e.message,true);}
  }
  if(form.id==='edit-resume-form'){
    const f=new FormData(form),button=form.querySelector('[type="submit"]');button.disabled=true;
    try{await api(`/api/resumes/${form.dataset.id}/update`,{text:f.get('text'),title:f.get('title')});document.querySelector('#modal-root').innerHTML='';await refresh();render();toast('已保存并重新解析');}
    catch(e){button.disabled=false;toast(e.message,true);}
  }
});
document.addEventListener('input',event=>{
  if(event.target.id==='answer-text'){try{localStorage.setItem(draftKey(),event.target.value);}catch{}updateCount();}
  if(event.target.id==='resume-search'){
    const pos=event.target.selectionStart;state.search=event.target.value;render();const input=document.querySelector('#resume-search');input.focus();input.setSelectionRange(pos,pos);
  }
});
document.addEventListener('change',event=>{if(event.target.id==='resume-files')importFiles(event.target.files);});
document.addEventListener('dragover',event=>{const drop=event.target.closest('#drop-zone');if(drop){event.preventDefault();drop.classList.add('drag');}});
document.addEventListener('dragleave',event=>{event.target.closest('#drop-zone')?.classList.remove('drag');});
document.addEventListener('drop',event=>{if(event.target.closest('#drop-zone')){event.preventDefault();importFiles(event.dataTransfer.files);}});
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!state.busy)document.querySelector('#modal-root').innerHTML='';});
window.addEventListener('hashchange',loadRoute);
loadRoute();
