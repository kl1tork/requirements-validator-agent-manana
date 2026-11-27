"""HTML-страница веб-приложения Manana (одна страница, без внешних зависимостей).

Плейсхолдеры: {{NAME}}, {{VER}}, {{EXT}}, {{LOGO}}, {{FAVICON}}, {{CRIT}} (JSON: код критерия → название).
"""

PAGE = r"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>{{NAME}} — проверка требований</title><link rel="icon" href="{{FAVICON}}">
<link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#0a6b45">
<link rel="apple-touch-icon" href="/apple-touch-icon.png"><meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes"><meta name="apple-mobile-web-app-status-bar-style" content="black-translucent"><meta name="apple-mobile-web-app-title" content="Manana">
<style>
:root{
 --brand:#0a6b45;--brand-2:#0e8a5a;--brand-ink:#063d28;--gold:#c9a227;--gold-soft:#f6edcc;
 --bg:#f4f6f3;--surface:#ffffff;--surface-2:#f8faf7;--text:#13201a;--muted:#5f6e66;--faint:#8b998f;--line:#e2e8e3;
 --crit:#c62828;--crit-bg:#fdecec;--major:#c76a00;--major-bg:#fff3e0;--minor:#5b6bbf;--minor-bg:#eef0fb;--ok:#1f8a4c;--ok-bg:#e7f6ec;
 --shadow:0 1px 2px rgba(16,32,24,.06),0 8px 24px rgba(16,32,24,.06);--r:16px;
}
@media (prefers-color-scheme:dark){:root{
 --bg:#0b1310;--surface:#121d18;--surface-2:#16231d;--text:#e6eee8;--muted:#9fb1a6;--faint:#728479;--line:#22342b;
 --crit:#ff8a80;--crit-bg:#3a1d1d;--major:#ffb74d;--major-bg:#3a2a14;--minor:#a5b0ff;--minor-bg:#22264a;--ok:#6fd49b;--ok-bg:#17352a;--gold-soft:#3a3218;
 --shadow:0 1px 2px rgba(0,0,0,.3),0 8px 24px rgba(0,0,0,.25)}}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,Arial,sans-serif;-webkit-font-smoothing:antialiased}
button,input{font:inherit;color:inherit}
.wrap{max-width:1120px;margin:0 auto;padding:0 24px}
/* header */
.top{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--surface) 82%,transparent);backdrop-filter:saturate(1.4) blur(12px);border-bottom:1px solid var(--line)}
.top .wrap{display:flex;align-items:center;gap:12px;height:64px}
.brand{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px;letter-spacing:-.01em}
.brand small{display:block;font-weight:500;font-size:12px;color:var(--muted);letter-spacing:0}
.top .sp{flex:1}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;border:1px solid var(--line);border-radius:999px;padding:5px 11px;color:var(--muted);background:var(--surface)}
.pill .dot{width:7px;height:7px;border-radius:50%;background:var(--ok);box-shadow:0 0 0 3px var(--ok-bg)}
.pill.busy .dot{background:var(--gold);box-shadow:0 0 0 3px var(--gold-soft);animation:pulse 1.2s infinite}
@keyframes pulse{50%{opacity:.35}}
/* hero */
.hero{position:relative;overflow:hidden;background:radial-gradient(1200px 400px at 85% -10%,rgba(201,162,39,.18),transparent 60%),linear-gradient(160deg,var(--brand-ink),var(--brand) 70%,var(--brand-2));color:#fff}
.hero .wrap{display:grid;grid-template-columns:1.05fr .95fr;gap:40px;padding-top:56px;padding-bottom:64px;align-items:center}
.eyebrow{display:inline-flex;gap:8px;align-items:center;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--gold);background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.14);padding:6px 12px;border-radius:999px}
.hero h1{font-size:44px;line-height:1.08;letter-spacing:-.025em;margin:18px 0 14px}
.hero h1 em{font-style:normal;color:var(--gold)}
.hero p.lead{font-size:17px;color:rgba(255,255,255,.82);margin:0 0 24px;max-width:520px}
.feats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;max-width:540px}
.feat{background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:12px}
.feat b{display:block;font-size:22px;letter-spacing:-.02em}.feat span{font-size:12px;color:rgba(255,255,255,.72)}
/* upload card */
.panel{background:var(--surface);color:var(--text);border-radius:20px;box-shadow:0 30px 60px rgba(0,0,0,.25);padding:22px;border:1px solid var(--line)}
.panel h2{margin:0 0 4px;font-size:18px;letter-spacing:-.01em}.panel .sub{margin:0 0 16px;color:var(--muted);font-size:13px}
.drop{position:relative;border:1.5px dashed var(--line);border-radius:14px;padding:30px 18px;text-align:center;cursor:pointer;transition:border-color .2s,background .2s,transform .2s;background:var(--surface-2)}
.drop:hover,.drop:focus-visible{border-color:var(--brand);outline:none}
.drop.over{border-color:var(--brand);background:color-mix(in srgb,var(--brand) 8%,var(--surface));transform:scale(1.01)}
.drop .ic{width:52px;height:52px;margin:0 auto 10px;border-radius:14px;display:grid;place-items:center;background:color-mix(in srgb,var(--brand) 12%,transparent);color:var(--brand);transition:transform .3s}
.drop:hover .ic,.drop.over .ic{transform:translateY(-3px)}
.drop b{display:block;font-size:15px}.drop small{color:var(--faint);font-size:12px}
#file{display:none}
.chip{display:none;align-items:center;gap:12px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-top:12px;background:var(--surface);animation:rise .25s ease}
.chip.on{display:flex}.chip .ft{width:38px;height:38px;border-radius:10px;display:grid;place-items:center;font-size:11px;font-weight:700;color:#fff;background:var(--brand);text-transform:uppercase}
.chip .nm{flex:1;min-width:0}.chip .nm b{display:block;font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.chip .nm span{font-size:12px;color:var(--muted)}
.x{border:0;background:transparent;cursor:pointer;color:var(--faint);width:30px;height:30px;border-radius:8px}.x:hover{background:var(--surface-2);color:var(--text)}
.actions{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;border-radius:11px;padding:11px 18px;font-weight:600;font-size:14px;border:1px solid var(--line);background:var(--surface);cursor:pointer;text-decoration:none;color:var(--text);transition:transform .12s,box-shadow .2s,background .2s,opacity .2s}
.btn:hover{transform:translateY(-1px);box-shadow:var(--shadow)}.btn:active{transform:none}
.btn.primary{background:linear-gradient(180deg,var(--brand-2),var(--brand));border-color:transparent;color:#fff;flex:1}
.btn.primary:disabled{opacity:.45;cursor:not-allowed;transform:none;box-shadow:none}
.btn.ghost{background:transparent}
.opt{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:12.5px;color:var(--muted);cursor:pointer;user-select:none}
.switch{position:relative;width:34px;height:20px;border-radius:999px;background:var(--line);transition:.2s;flex:none}
.switch::after{content:"";position:absolute;top:2px;left:2px;width:16px;height:16px;border-radius:50%;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25);transition:.2s}
#fresh{display:none}#fresh:checked+.switch{background:var(--brand)}#fresh:checked+.switch::after{left:16px}
.privacy{display:flex;gap:8px;align-items:flex-start;margin-top:14px;padding-top:14px;border-top:1px solid var(--line);font-size:12px;color:var(--faint)}
/* sections */
section.block{margin:28px 0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--r);box-shadow:var(--shadow)}
.hidden{display:none!important}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.rise{animation:rise .35s ease both}
/* how it works */
.how{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-top:-28px;position:relative;z-index:2}
.how .card{padding:18px 20px;display:flex;gap:14px}
.how .n{flex:none;width:34px;height:34px;border-radius:10px;display:grid;place-items:center;font-weight:700;background:var(--gold-soft);color:#8a6d0f}
@media (prefers-color-scheme:dark){.how .n{color:var(--gold)}}
.how b{display:block;margin-bottom:2px}.how span{font-size:13px;color:var(--muted)}
/* progress */
.prog{padding:24px}
.prog-head{display:flex;align-items:center;gap:14px;margin-bottom:18px}
.spinner{width:40px;height:40px;border-radius:50%;border:3px solid var(--line);border-top-color:var(--brand);animation:spin 1s linear infinite;flex:none}
@keyframes spin{to{transform:rotate(360deg)}}
.prog-head h3{margin:0;font-size:17px}.prog-head p{margin:2px 0 0;color:var(--muted);font-size:13px}
.timer{margin-left:auto;font:600 22px/1 ui-monospace,Menlo,monospace;color:var(--brand);letter-spacing:.02em}
.bar{height:6px;background:var(--surface-2);border-radius:999px;overflow:hidden;border:1px solid var(--line)}
.bar i{display:block;height:100%;width:0;background:linear-gradient(90deg,var(--brand),var(--gold));transition:width .6s cubic-bezier(.2,.8,.2,1);position:relative}
.bar i::after{content:"";position:absolute;inset:0;background:linear-gradient(90deg,transparent,rgba(255,255,255,.45),transparent);animation:shine 1.6s infinite}
@keyframes shine{from{transform:translateX(-100%)}to{transform:translateX(100%)}}
.steps{list-style:none;margin:18px 0 0;padding:0;display:grid;grid-template-columns:repeat(6,1fr);gap:8px}
.steps li{position:relative;padding:12px;border-radius:12px;border:1px solid var(--line);background:var(--surface-2);font-size:12.5px;color:var(--faint);transition:.3s}
.steps li .si{width:24px;height:24px;border-radius:50%;display:grid;place-items:center;font-size:12px;font-weight:700;background:var(--line);color:var(--muted);margin-bottom:8px;transition:.3s}
.steps li.active{border-color:var(--brand);color:var(--text);background:color-mix(in srgb,var(--brand) 7%,var(--surface))}
.steps li.active .si{background:var(--brand);color:#fff;box-shadow:0 0 0 4px color-mix(in srgb,var(--brand) 20%,transparent);animation:pulse 1.4s infinite}
.steps li.done{color:var(--text)}.steps li.done .si{background:var(--ok);color:#fff}
details.log{margin-top:16px}details.log summary{cursor:pointer;font-size:13px;color:var(--muted);user-select:none}
.logbox{font:12px/1.55 ui-monospace,Menlo,monospace;background:var(--surface-2);border:1px solid var(--line);border-radius:10px;padding:10px 12px;max-height:200px;overflow:auto;color:var(--muted);white-space:pre-wrap;margin-top:8px}
/* error */
/* mascot */
.mascot{position:relative;display:inline-block;cursor:pointer;-webkit-tap-highlight-color:transparent}
.mascot svg{display:block;width:100%;height:auto;overflow:visible}
.mascot [class^="m-"],.mascot [class*=" m-"]{transform-box:fill-box}
.m-bob{transform-origin:50% 100%;animation:m-bob 3.2s ease-in-out infinite}
@keyframes m-bob{0%,100%{transform:translateY(0) scale(1,1)}50%{transform:translateY(-6px) scale(.98,1.02)}}
.m-shadow{transform-origin:center;animation:m-sh 3.2s ease-in-out infinite}
@keyframes m-sh{50%{transform:scale(.85);opacity:.12}}
.m-sprout{transform-origin:50% 100%;animation:m-sway 2.6s ease-in-out infinite}
@keyframes m-sway{0%,100%{transform:rotate(-7deg)}50%{transform:rotate(7deg)}}
.m-lid{transform-origin:center;transition:transform .09s}
.mascot.blink .m-lid{transform:scaleY(.08)}
.m-look{transition:transform .12s ease-out}
.m-arm-r{transform-origin:center}.m-arm-l{transform-origin:center}
.mascot:hover .m-arm-r,.mascot.wave .m-arm-r{animation:m-wave .5s ease-in-out 3}
@keyframes m-wave{50%{transform:translate(2px,-10px) rotate(-14deg)}}
.mascot.jump .m-bob{animation:m-jump .6s cubic-bezier(.3,1.6,.5,1)}
@keyframes m-jump{0%{transform:scale(1.08,.9)}35%{transform:translateY(-22px) scale(.94,1.08)}70%{transform:translateY(0) scale(1.06,.94)}100%{transform:none}}
.m-tool,.m-sweat,.m-spark,.m-dots{opacity:0;transition:opacity .3s}
.mascot.work .m-tool{opacity:1}.mascot.work .m-tool{transform-origin:20% 80%;animation:m-scan 1.6s ease-in-out infinite}
@keyframes m-scan{0%,100%{transform:translate(0,0) rotate(0)}25%{transform:translate(-14px,6px) rotate(-8deg)}50%{transform:translate(-26px,0) rotate(0)}75%{transform:translate(-12px,-6px) rotate(6deg)}}
.mascot.work .m-bob{animation-duration:1.1s}.mascot.work .m-dots{opacity:1}
.m-dots circle{animation:m-dot 1.2s infinite}.m-dots circle:nth-child(2){animation-delay:.2s}.m-dots circle:nth-child(3){animation-delay:.4s}
@keyframes m-dot{0%,100%{opacity:.25;transform:translateY(0)}50%{opacity:1;transform:translateY(-4px)}}
.mascot.happy .m-spark{opacity:1}.mascot.happy .m-bob{animation:m-hop .9s ease-in-out infinite}
@keyframes m-hop{0%,100%{transform:translateY(0)}40%{transform:translateY(-12px) rotate(-3deg)}60%{transform:translateY(-12px) rotate(3deg)}}
.m-spark path{transform-origin:center;animation:m-tw 1.4s ease-in-out infinite}.m-spark path:nth-child(2){animation-delay:.5s}.m-spark path:nth-child(3){animation-delay:.9s}
@keyframes m-tw{0%,100%{transform:scale(.4) rotate(0);opacity:.3}50%{transform:scale(1.1) rotate(45deg);opacity:1}}
.mascot.sad .m-sweat{opacity:1;animation:m-drip 1.8s ease-in infinite}
@keyframes m-drip{0%{transform:translateY(-4px);opacity:0}30%{opacity:1}100%{transform:translateY(10px);opacity:0}}
.mascot.sad .m-bob{animation:m-slump 2.4s ease-in-out infinite}
@keyframes m-slump{0%,100%{transform:translateY(2px) scale(1.03,.97)}50%{transform:translateY(4px) scale(1.05,.95)}}
.mascot.sad .m-sprout{animation:none;transform:rotate(28deg)}
.perch{position:absolute;right:6px;top:-172px;width:196px;z-index:3}
#up{margin-top:130px}
.panel{position:relative}
.bubble{position:absolute;right:184px;top:28px;width:max-content;max-width:230px;background:#fff;color:#13201a;font-size:13px;font-weight:600;line-height:1.35;padding:9px 13px;border-radius:14px 14px 4px 14px;box-shadow:0 10px 30px rgba(0,0,0,.25);opacity:0;transform:translateY(6px) scale(.96);transform-origin:100% 100%;transition:.25s;pointer-events:none}
.bubble.on{opacity:1;transform:none}
.bubble::after{content:"";position:absolute;right:-6px;bottom:6px;border:7px solid transparent;border-left-color:#fff;border-right:0}
.brand .mascot{width:38px;margin:-6px 0 -2px}
.prog-head .mascot{width:70px;flex:none;margin:-8px 0}
.verdict .vi.mhost{background:none;width:76px;height:76px;margin:-10px 0}
.verdict .vi.mhost .mascot{width:76px}
@media (prefers-reduced-motion:reduce){.mascot *{animation:none!important}}
@media (max-width:900px){.perch{top:-132px;width:150px}.bubble{right:140px}#up{margin-top:116px}}
/* chat */
.fab{position:fixed;right:22px;bottom:18px;z-index:40;width:112px;border:0;background:none;padding:0;cursor:pointer;filter:drop-shadow(0 12px 22px rgba(0,0,0,.28));transition:transform .25s}
.fab:hover{transform:translateY(-3px)}.fab .mascot{width:112px}
.fab .tag{position:absolute;right:96px;bottom:58px;white-space:nowrap;background:var(--surface);color:var(--text);border:1px solid var(--line);font-size:13px;font-weight:600;padding:8px 12px;border-radius:12px 12px 4px 12px;box-shadow:var(--shadow);animation:rise .4s ease both 1.2s}
.fab .ping{position:absolute;right:16px;top:20px;width:14px;height:14px;border-radius:50%;background:var(--gold);border:2px solid var(--surface)}
.fab .ping::after{content:"";position:absolute;inset:-2px;border-radius:50%;border:2px solid var(--gold);animation:ping 1.6s infinite}
@keyframes ping{to{transform:scale(2.4);opacity:0}}
body.chat-open .fab{transform:scale(.0);pointer-events:none}
.chat{position:fixed;right:22px;bottom:22px;z-index:45;width:min(410px,calc(100vw - 24px));height:min(640px,calc(100vh - 44px));display:flex;flex-direction:column;background:var(--surface);border:1px solid var(--line);border-radius:22px;box-shadow:0 30px 80px rgba(0,0,0,.35);overflow:hidden;transform-origin:100% 100%;transform:scale(.85) translateY(20px);opacity:0;pointer-events:none;transition:.28s cubic-bezier(.2,.9,.3,1.2)}
body.chat-open .chat{transform:none;opacity:1;pointer-events:auto}
.chat-head{display:flex;align-items:center;gap:12px;padding:14px 16px 12px;background:linear-gradient(160deg,var(--brand-ink),var(--brand));color:#fff}
.chat-head .mascot{width:64px;margin:-6px -4px -10px -6px}
.chat-head b{display:block;font-size:16px}.chat-head small{display:flex;align-items:center;gap:6px;font-size:12px;opacity:.85}
.chat-head small i{width:7px;height:7px;border-radius:50%;background:#5ff0bd;box-shadow:0 0 0 3px rgba(95,240,189,.25)}
.chat-head .sp{flex:1}.chat-head button{border:0;background:rgba(255,255,255,.12);color:#fff;width:32px;height:32px;border-radius:10px;cursor:pointer;font-size:15px}
.chat-head button:hover{background:rgba(255,255,255,.22)}
.msgs{flex:1;overflow:auto;padding:16px;display:flex;flex-direction:column;gap:10px;background:var(--bg)}
.msg{max-width:85%;padding:10px 13px;border-radius:16px;font-size:14px;line-height:1.5;animation:rise .25s ease both;word-wrap:break-word}
.msg.bot{align-self:flex-start;background:var(--surface);border:1px solid var(--line);border-bottom-left-radius:5px}
.msg.me{align-self:flex-end;background:linear-gradient(180deg,var(--brand-2),var(--brand));color:#fff;border-bottom-right-radius:5px}
.msg.err{border-color:color-mix(in srgb,var(--crit) 40%,var(--line));color:var(--crit)}
.msg ul{margin:6px 0;padding-left:18px}.msg p{margin:0 0 6px}.msg p:last-child{margin:0}
.msg code{font:12px ui-monospace,Menlo,monospace;background:var(--surface-2);padding:1px 5px;border-radius:5px}
.msg .iid{font:600 12px ui-monospace,Menlo,monospace;color:var(--brand);cursor:pointer;text-decoration:underline dotted}
.typing{display:inline-flex;gap:4px;padding:4px 2px}.typing i{width:7px;height:7px;border-radius:50%;background:var(--faint);animation:m-dot 1.1s infinite}
.typing i:nth-child(2){animation-delay:.15s}.typing i:nth-child(3){animation-delay:.3s}
.sugg{display:flex;gap:6px;flex-wrap:wrap;padding:10px 14px 0;background:var(--surface)}
.sugg button{border:1px solid var(--line);background:var(--surface-2);border-radius:999px;padding:6px 11px;font-size:12.5px;cursor:pointer;color:var(--text);transition:.15s}
.sugg button:hover{border-color:var(--brand);color:var(--brand)}
.composer{display:flex;gap:8px;padding:12px 14px 14px;background:var(--surface);align-items:flex-end}
.composer textarea{flex:1;resize:none;border:1px solid var(--line);border-radius:14px;padding:10px 12px;font:inherit;font-size:14px;max-height:120px;background:var(--surface-2);color:var(--text);outline:0}
.composer textarea:focus{border-color:var(--brand)}
.composer button{flex:none;width:42px;height:42px;border-radius:12px;border:0;background:linear-gradient(180deg,var(--brand-2),var(--brand));color:#fff;cursor:pointer;display:grid;place-items:center}
.composer button:disabled{opacity:.45;cursor:default}
.chat-ctx{font-size:11.5px;color:var(--faint);padding:6px 16px;background:var(--surface);border-top:1px solid var(--line)}
@media (max-width:520px){.fab{width:84px}.fab .mascot{width:84px}.fab .tag{display:none}.chat{right:12px;bottom:12px}}
/* phone */
@media (max-width:640px){
 body{font-size:14.5px}
 .top .wrap{height:56px;padding-top:env(safe-area-inset-top)}.top{padding-top:0}
 .top .pill:last-child,.brand small{display:none}
 #statusText{display:none}.top .pill{padding:7px}
 .hero .wrap{padding-top:22px;padding-bottom:36px;gap:18px}
 .hero h1{font-size:29px;margin:12px 0 10px}.hero p.lead{font-size:15px;margin-bottom:16px}
 .eyebrow{font-size:10.5px}
 .perch{width:128px;top:-112px;right:0}.bubble{right:118px;top:18px;max-width:170px;font-size:12px}
 #up{margin-top:104px}.panel{padding:18px;border-radius:18px}
 .drop{padding:22px 14px}
 .actions .btn{padding:13px 16px}
 .how .card{padding:14px 16px}
 .prog{padding:18px}.timer{font-size:18px}
 .verdict{padding:16px}.verdict h2{font-size:17px}.verdict .vi.mhost{width:60px;height:60px}.verdict .vi.mhost .mascot{width:60px}
 .kpi{padding:12px 14px}.kpi b{font-size:24px}
 .tabs{margin:18px -16px 14px;padding:0 16px}
 .toolbar{gap:8px}.seg{width:100%;overflow-x:auto}.seg button{padding:7px 9px;font-size:12px}
 table.req th:nth-child(3),table.req td:nth-child(3){display:none}
 iframe{height:70vh}
 .fab{right:12px;bottom:calc(10px + env(safe-area-inset-bottom));width:80px}.fab .mascot{width:80px}
 .chat{inset:0;width:100%;height:100%;max-height:none;border-radius:0;border:0;padding-bottom:env(safe-area-inset-bottom)}
 .chat-head{padding-top:calc(14px + env(safe-area-inset-top))}
 .composer textarea{font-size:16px}
 .msg{max-width:90%}
 .toast{bottom:calc(16px + env(safe-area-inset-bottom))}
}
@media (display-mode:standalone){.top{padding-top:env(safe-area-inset-top)}}
.toast{position:fixed;left:50%;bottom:24px;transform:translateX(-50%) translateY(20px);opacity:0;pointer-events:none;z-index:50;max-width:min(560px,calc(100% - 32px));background:var(--crit-bg);color:var(--crit);border:1px solid color-mix(in srgb,var(--crit) 30%,transparent);border-radius:12px;padding:12px 16px;font-size:14px;font-weight:500;box-shadow:var(--shadow);transition:.3s}
.toast.on{opacity:1;transform:translateX(-50%);pointer-events:auto}
/* results */
.verdict{display:flex;gap:18px;align-items:center;padding:22px 24px;border-radius:var(--r);border:1px solid var(--line);background:var(--surface);box-shadow:var(--shadow);position:relative;overflow:hidden}
.verdict::before{content:"";position:absolute;inset:0 auto 0 0;width:5px;background:var(--vc,var(--ok))}
.verdict .vi{flex:none;width:52px;height:52px;border-radius:14px;display:grid;place-items:center;background:var(--vbg,var(--ok-bg));color:var(--vc,var(--ok))}
.verdict small{display:block;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted)}
.verdict h2{margin:2px 0 0;font-size:20px;letter-spacing:-.01em}
.verdict .meta{margin-left:auto;text-align:right;font-size:12px;color:var(--faint)}
.verdict .dl{display:flex;gap:8px;margin-top:8px;justify-content:flex-end;flex-wrap:wrap}
.verdict .dl .btn{padding:7px 12px;font-size:12.5px}
.kpis{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:16px 0}
.kpi{padding:16px 18px;cursor:pointer;transition:transform .15s,border-color .2s}
.kpi:hover{transform:translateY(-2px);border-color:var(--brand)}
.kpi span{font-size:12.5px;color:var(--muted);display:flex;align-items:center;gap:6px}
.kpi b{display:block;font-size:30px;letter-spacing:-.03em;margin-top:4px;font-variant-numeric:tabular-nums}
.kpi .sw{width:8px;height:8px;border-radius:2px}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin:24px 0 18px;overflow-x:auto}
.tab{border:0;background:none;padding:10px 14px;font-weight:600;font-size:14px;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px;white-space:nowrap}
.tab:hover{color:var(--text)}.tab.on{color:var(--brand);border-bottom-color:var(--brand)}
.tab .c{display:inline-block;margin-left:6px;font-size:11px;padding:1px 7px;border-radius:999px;background:var(--surface-2);border:1px solid var(--line);color:var(--muted)}
.grid2{display:grid;grid-template-columns:1.3fr 1fr;gap:16px}
.pad{padding:20px 22px}.pad h3{margin:0 0 12px;font-size:15px}
.summary{margin:0;color:var(--text);line-height:1.65}
ol.prio{margin:0;padding:0;list-style:none;counter-reset:p}
ol.prio li{counter-increment:p;display:flex;gap:12px;padding:12px 0;border-top:1px solid var(--line);font-size:14px}
ol.prio li:first-child{border-top:0;padding-top:0}
ol.prio li::before{content:counter(p);flex:none;width:24px;height:24px;border-radius:7px;display:grid;place-items:center;font-size:12px;font-weight:700;background:var(--gold-soft);color:#8a6d0f}
.ref{display:inline-block;font:600 11px/1 ui-monospace,Menlo,monospace;padding:3px 6px;border-radius:6px;background:var(--surface-2);border:1px solid var(--line);color:var(--muted);cursor:pointer;margin:4px 4px 0 0}
.ref:hover{border-color:var(--brand);color:var(--brand)}
.crit-row{display:grid;grid-template-columns:1fr 120px 28px;gap:10px;align-items:center;font-size:13px;padding:6px 0;cursor:pointer;border-radius:8px}
.crit-row:hover .cn{color:var(--brand)}
.crit-row .cb{height:8px;border-radius:999px;background:var(--surface-2);overflow:hidden;border:1px solid var(--line)}
.crit-row .cb i{display:block;height:100%;background:linear-gradient(90deg,var(--major),var(--crit));border-radius:999px;transition:width .8s cubic-bezier(.2,.8,.2,1)}
.crit-row b{text-align:right;font-variant-numeric:tabular-nums}
.setc{display:flex;gap:10px;padding:10px 0;border-top:1px solid var(--line);font-size:13px}.setc:first-of-type{border-top:0}
.setc .tx b{display:block;font-size:13.5px}.setc .tx span{color:var(--muted)}
.st{flex:none;font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;height:fit-content;white-space:nowrap}
.st.ok{background:var(--ok-bg);color:var(--ok)}.st.violation{background:var(--crit-bg);color:var(--crit)}.st.unconfirmed{background:var(--major-bg);color:var(--major)}
/* issues */
.toolbar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:11px;padding:3px;background:var(--surface)}
.seg button{border:0;background:none;padding:7px 12px;border-radius:8px;font-size:13px;font-weight:600;color:var(--muted);cursor:pointer;display:inline-flex;gap:6px;align-items:center}
.seg button.on{background:var(--surface-2);color:var(--text);box-shadow:0 1px 2px rgba(0,0,0,.08)}
.seg .sw{width:8px;height:8px;border-radius:2px}
.search{flex:1;min-width:200px;display:flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:11px;padding:0 12px;background:var(--surface)}
.search input{border:0;outline:0;background:none;padding:9px 0;width:100%;font-size:14px}
.search:focus-within{border-color:var(--brand)}
.filter-tag{display:none;align-items:center;gap:6px;font-size:12.5px;font-weight:600;padding:6px 10px;border-radius:999px;background:color-mix(in srgb,var(--brand) 10%,transparent);color:var(--brand)}
.filter-tag.on{display:inline-flex}.filter-tag button{border:0;background:none;color:inherit;cursor:pointer;padding:0;font-size:14px}
.issue{margin-bottom:10px;overflow:hidden;transition:border-color .2s}
.issue[open]{border-color:color-mix(in srgb,var(--sc) 45%,var(--line))}
.issue summary{list-style:none;cursor:pointer;display:flex;gap:12px;align-items:flex-start;padding:14px 16px}
.issue summary::-webkit-details-marker{display:none}
.issue .sev{flex:none;font-size:11px;font-weight:700;padding:3px 8px;border-radius:6px;background:var(--sbg);color:var(--sc);margin-top:1px}
.issue .ttl{flex:1;min-width:0;font-size:14px}
.issue .ttl small{display:block;color:var(--faint);font-size:12px;margin-top:3px}
.issue .chev{flex:none;transition:transform .2s;color:var(--faint);margin-top:2px}
.issue[open] .chev{transform:rotate(180deg)}
.issue .body{padding:0 16px 16px 16px;display:grid;gap:12px}
.issue .q{border-left:3px solid var(--sc);background:var(--surface-2);padding:10px 12px;border-radius:0 8px 8px 0;font-size:13.5px}
.issue .q span{display:block;font-size:11.5px;color:var(--faint);margin-bottom:2px}
.issue .fix{display:flex;gap:10px;background:var(--ok-bg);border-radius:10px;padding:10px 12px;font-size:13.5px}
.issue .fix b{color:var(--ok);flex:none}
.sev-critical{--sc:var(--crit);--sbg:var(--crit-bg)}.sev-major{--sc:var(--major);--sbg:var(--major-bg)}.sev-minor{--sc:var(--minor);--sbg:var(--minor-bg)}
.empty{text-align:center;color:var(--muted);padding:40px 0}
/* requirements */
table.req{width:100%;border-collapse:collapse;font-size:13.5px}
table.req th{text-align:left;font-size:12px;color:var(--muted);font-weight:600;padding:10px 14px;border-bottom:1px solid var(--line);background:var(--surface-2)}
table.req td{padding:12px 14px;border-bottom:1px solid var(--line);vertical-align:top}
table.req tr.rq{cursor:pointer;transition:background .15s}table.req tr.rq:hover{background:var(--surface-2)}
table.req .rid{font:600 12px ui-monospace,Menlo,monospace;color:var(--brand);white-space:nowrap}
.dots{display:flex;gap:4px;flex-wrap:wrap}.dots i{display:inline-flex;min-width:22px;justify-content:center;font-style:normal;font-size:11px;font-weight:700;padding:2px 6px;border-radius:6px}
iframe{width:100%;height:80vh;border:1px solid var(--line);border-radius:var(--r);background:#fff}
footer{color:var(--faint);font-size:12px;padding:24px 0 48px;text-align:center}
@media (max-width:900px){.hero .wrap{grid-template-columns:1fr;gap:28px;padding-top:36px}.hero h1{font-size:34px}.how{grid-template-columns:1fr;margin-top:16px}
 .kpis{grid-template-columns:repeat(2,1fr)}.grid2{grid-template-columns:1fr}.steps{grid-template-columns:repeat(3,1fr)}.verdict{flex-wrap:wrap}.verdict .meta{margin-left:0;text-align:left}.verdict .dl{justify-content:flex-start}}
@media (max-width:520px){.wrap{padding:0 16px}.feats{grid-template-columns:1fr 1fr 1fr}.feat b{font-size:18px}.steps{grid-template-columns:repeat(2,1fr)}}
</style></head><body>
<header class="top"><div class="wrap">
 <div class="brand"><span class="mascot" data-m="head"></span><div>{{NAME}}<small>Агент проверки требований</small></div></div>
 <div class="sp"></div>
 <span class="pill" id="status"><span class="dot"></span><span id="statusText">Готова к работе</span></span>
 <span class="pill">v{{VER}}</span>
</div></header>

<div class="hero"><div class="wrap">
 <div>
  <span class="eyebrow">ISO/IEC/IEEE 29148 · IEEE 830</span>
  <h1>Найдите ошибки в требованиях <em>до&nbsp;начала разработки</em></h1>
  <p class="lead">{{NAME}} разбирает документ на отдельные требования, проверяет каждое и весь набор целиком, а затем показывает дефекты с цитатами и готовыми исправлениями.</p>
  <div class="feats">
   <div class="feat"><b>18</b><span>критериев качества</span></div>
   <div class="feat"><b>1–5</b><span>минут на документ</span></div>
   <div class="feat"><b>2</b><span>стандарта качества</span></div>
  </div>
 </div>
 <div class="panel" id="up">
  <div class="perch"><div class="bubble" id="bub"></div><span class="mascot" id="hero-m" data-m="hero" title="Нажмите на меня"></span></div>
  <h2>Новая проверка</h2><p class="sub">Форматы: {{EXT}} · до 20 МБ</p>
  <div class="drop" id="drop" tabindex="0" role="button" aria-label="Выбрать файл">
   <div class="ic"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 16V4M7 9l5-5 5 5"/><path d="M20 16v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3"/></svg></div>
   <b>Перетащите документ сюда</b><small>или нажмите, чтобы выбрать файл</small>
  </div>
  <input type="file" id="file">
  <div class="chip" id="chip"><span class="ft" id="ftype">MD</span><div class="nm"><b id="fname"></b><span id="fsize"></span></div>
   <button class="x" id="clear" title="Убрать файл" aria-label="Убрать файл">✕</button></div>
  <div class="actions">
   <button class="btn primary" id="go" disabled>Проверить документ
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button>
   <button class="btn ghost hidden" id="sample">Пример</button>
  </div>
  <label class="opt"><input type="checkbox" id="fresh"><span class="switch"></span>Заново спросить модель (без кэша)</label>
  <div class="privacy"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>
   <span>Приложение работает на вашем компьютере. Документ уходит только в выбранную языковую модель.</span></div>
 </div>
</div></div>

<main class="wrap">
 <div class="how" id="how">
  <div class="card"><span class="n">1</span><div><b>Загрузка</b><span>PDF, Word, Markdown или HTML с требованиями</span></div></div>
  <div class="card"><span class="n">2</span><div><b>Анализ</b><span>Линтер, нарезка, проверка требований и набора</span></div></div>
  <div class="card"><span class="n">3</span><div><b>Отчёт</b><span>Вердикт, дефекты по важности, что исправить</span></div></div>
 </div>

 <section class="block hidden" id="prog"><div class="card prog">
  <div class="prog-head"><span class="mascot work" data-m="prog"></span><div><h3 id="stage">Подготовка…</h3><p id="pfile"></p></div><div class="timer" id="timer">00:00</div></div>
  <div class="bar"><i id="bar"></i></div>
  <ol class="steps" id="steps"></ol>
  <details class="log"><summary>Технический журнал</summary><div class="logbox" id="log"></div></details>
 </div></section>

 <section class="block hidden" id="done">
  <div class="verdict rise" id="verdict">
   <div class="vi mhost"><span class="mascot" id="vm" data-m="verdict"></span></div>
   <div><small>Вердикт</small><h2 id="vtext"></h2></div>
   <div class="meta"><div id="vmeta"></div>
    <div class="dl"><a class="btn" id="aopen" target="_blank">Открыть отчёт ↗</a><a class="btn" id="ahtml">HTML</a><a class="btn" id="amd">Markdown</a><a class="btn" id="ajson">JSON</a></div></div>
  </div>
  <div class="kpis rise" id="kpis"></div>
  <nav class="tabs" id="tabs">
   <button class="tab on" data-t="ov">Обзор</button>
   <button class="tab" data-t="is">Замечания<span class="c" id="cIs">0</span></button>
   <button class="tab" data-t="rq">Требования<span class="c" id="cRq">0</span></button>
   <button class="tab" data-t="full">Полный отчёт</button>
  </nav>
  <div id="t-ov" class="pane">
   <div class="grid2">
    <div class="card pad"><h3>Краткий вывод</h3><p class="summary" id="sum"></p><h3 style="margin-top:22px">Что исправить в первую очередь</h3><ol class="prio" id="prio"></ol></div>
    <div style="display:grid;gap:16px;align-content:start">
     <div class="card pad"><h3>Нарушения по критериям</h3><div id="crit"></div></div>
     <div class="card pad"><h3>Набор требований целиком</h3><div id="setc"></div></div>
    </div>
   </div>
  </div>
  <div id="t-is" class="pane hidden">
   <div class="toolbar">
    <div class="seg" id="sev"></div>
    <label class="search"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><input id="q" placeholder="Поиск по замечаниям…"></label>
    <span class="filter-tag" id="ftag"><span id="ftagText"></span><button id="ftagX" aria-label="Сбросить">✕</button></span>
   </div>
   <div id="issues"></div>
  </div>
  <div id="t-rq" class="pane hidden"><div class="card" style="overflow:auto"><table class="req"><thead><tr><th>ID</th><th>Требование</th><th>Раздел</th><th>Замечания</th></tr></thead><tbody id="reqs"></tbody></table></div></div>
  <div id="t-full" class="pane hidden"><iframe id="frame" title="Отчёт"></iframe></div>
 </section>
 <footer>{{NAME}} v{{VER}} · проверка по ISO/IEC/IEEE 29148:2018 и IEEE Std 830-1998</footer>
</main>
<button class="fab" id="fab" aria-label="Открыть чат с Manana"><span class="tag">Спросите меня ✨</span><span class="mascot" data-m="fab"></span><span class="ping"></span></button>
<div class="chat" id="chat" role="dialog" aria-label="Чат с Manana">
 <div class="chat-head"><span class="mascot" id="chat-m" data-m="chat"></span><div><b>Manana</b><small><i></i><span id="chatState">на связи · ИИ-агент</span></small></div><div class="sp"></div>
  <button id="chatReset" title="Новый диалог">↺</button><button id="chatClose" title="Закрыть">✕</button></div>
 <div class="msgs" id="msgs"></div>
 <div class="sugg" id="sugg"></div>
 <div class="composer"><textarea id="ci" rows="1" placeholder="Напишите Manana…"></textarea>
  <button id="cs" aria-label="Отправить"><svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg></button></div>
 <div class="chat-ctx" id="chatCtx">Отчёта пока нет — спрашивайте о требованиях и о том, как работает проверка.</div>
</div>
<div class="toast" id="toast" role="alert"></div>

<script>
const CRIT={{CRIT}};
const STEPS=['Чтение документа','Линтер формулировок','Нарезка требований','Проверка требований','Проверка набора','Запись отчёта'];
const SAY=['Читаю ваш документ…','Ищу размытые формулировки вроде «быстро» и «удобно»…','Разбираю текст на отдельные требования…','Проверяю каждое требование по 10 критериям…','Смотрю, нет ли противоречий между требованиями…','Пишу отчёт с цитатами и исправлениями…'];
const SEV={critical:['Критично','sev-critical','var(--crit)'],major:['Существенно','sev-major','var(--major)'],minor:['Незначительно','sev-minor','var(--minor)']};
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let file=null,timerId=null,t0=0,DATA=null,F={sev:'all',q:'',rid:null,crit:null};

const toast=m=>{const t=$('toast');t.textContent=m;t.classList.add('on');clearTimeout(t._h);t._h=setTimeout(()=>t.classList.remove('on'),6000)};
const status=(txt,busy)=>{$('statusText').textContent=txt;$('status').classList.toggle('busy',!!busy)};
const size=b=>b<1024?b+' Б':b<1048576?(b/1024).toFixed(1)+' КБ':(b/1048576).toFixed(1)+' МБ';

function pick(f){file=f||null;if(f&&window.say){setMood($('hero-m'),'happy');say('Отлично! Жмите «Проверить документ»');$('hero-m').classList.remove('jump');void $('hero-m').offsetWidth;$('hero-m').classList.add('jump')}else if(window.setMood&&document.querySelector('#hero-m svg'))setMood($('hero-m'),'idle');$('chip').classList.toggle('on',!!f);$('go').disabled=!f;
 if(f){$('fname').textContent=f.name;$('fsize').textContent=size(f.size)+' · готов к проверке';$('ftype').textContent=(f.name.split('.').pop()||'?').slice(0,4)}
 $('file').value=''}
$('drop').onclick=()=>$('file').click();
$('drop').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('file').click()}};
$('file').onchange=e=>pick(e.target.files[0]);$('clear').onclick=()=>pick(null);
['dragover','dragenter'].forEach(t=>$('drop').addEventListener(t,e=>{e.preventDefault();$('drop').classList.add('over')}));
['dragleave','drop'].forEach(t=>$('drop').addEventListener(t,e=>{e.preventDefault();$('drop').classList.remove('over')}));
$('drop').addEventListener('drop',e=>{if(e.dataTransfer.files[0])pick(e.dataTransfer.files[0])});

fetch('/sample',{method:'HEAD'}).then(r=>{if(r.ok)$('sample').classList.remove('hidden')}).catch(()=>{});
$('sample').onclick=async()=>{const r=await fetch('/sample');if(!r.ok)return toast('Пример недоступен.');
 const b=await r.blob();pick(new File([b],r.headers.get('X-Filename')||'requirements.md',{type:b.type}))};

function renderSteps(cur){$('steps').innerHTML=STEPS.map((s,i)=>{const n=i+1,c=n<cur?'done':n===cur?'active':'';
 return `<li class="${c}"><span class="si">${n<cur?'✓':n}</span>${s}</li>`}).join('')}
const tick=()=>{const s=Math.floor((Date.now()-t0)/1000);$('timer').textContent=String(Math.floor(s/60)).padStart(2,'0')+':'+String(s%60).padStart(2,'0')};

$('go').onclick=async()=>{
 if(!file)return toast('Сначала выберите файл.');
 $('go').disabled=true;$('done').classList.add('hidden');$('prog').classList.remove('hidden');$('how').classList.add('hidden');
 $('log').textContent='';$('bar').style.width='4%';$('stage').textContent='Manana берётся за работу…';$('pfile').textContent=file.name+' · '+size(file.size);
 renderSteps(1);setMood($('hero-m'),'work');t0=Date.now();tick();clearInterval(timerId);timerId=setInterval(tick,1000);status('Идёт проверка',true);
 $('prog').scrollIntoView({behavior:'smooth',block:'center'});
 let r;try{r=await fetch('/run'+($('fresh').checked?'?nocache':''),{method:'POST',headers:{'X-Filename':encodeURIComponent(file.name)},body:file})}
 catch(e){return fail('Не удалось связаться с приложением. Оно запущено?')}
 const j=await r.json();if(!r.ok)return fail(j.error||'Ошибка');poll(j.id)};

function fail(m){setMood($('hero-m'),'sad');say('Ой, что-то пошло не так…',5000);clearInterval(timerId);$('prog').classList.add('hidden');$('how').classList.remove('hidden');$('go').disabled=!file;status('Готова к работе');toast(m)}

async function poll(id){
 let s;try{s=await (await fetch('/status/'+id)).json()}catch(e){return setTimeout(()=>poll(id),2000)}
 $('log').textContent=s.log.join('\n');$('log').scrollTop=1e9;
 const st=[...s.log].reverse().find(l=>/^\d\/6/.test(l));
 if(st){const n=+st[0];$('stage').textContent=SAY[n-1];$('pfile').textContent=`Шаг ${n} из 6 · ${STEPS[n-1]} · ${file?file.name:''}`;$('bar').style.width=Math.max(4,(n-.5)/6*100)+'%';renderSteps(n)}
 if(s.state==='done'){$('bar').style.width='100%';renderSteps(7);clearInterval(timerId);setTimeout(()=>finish(id),450);return}
 if(s.state==='error')return fail('Проверка остановилась: '+s.error);
 setTimeout(()=>poll(id),1000)}

async function finish(id){
 RUN=id;$('chatCtx').textContent='Manana знает результаты последней проверки';if(document.body.classList.contains('chat-open'))greet();else $('msgs').innerHTML='';
 const b='/runs/'+id+'/';$('aopen').href=b+'report.html';$('ahtml').href=b+'report.html?dl=1';$('amd').href=b+'report.md?dl=1';$('ajson').href=b+'report.json?dl=1';$('frame').src=b+'report.html';
 try{DATA=await (await fetch(b+'report.json')).json()}catch(e){DATA=null}
 $('prog').classList.add('hidden');$('done').classList.remove('hidden');$('go').disabled=!file;status('Проверка завершена');
 if(DATA)render(DATA);else{showTab('full')}
 $('done').scrollIntoView({behavior:'smooth'})}

function allIssues(d){const seen=new Set(),out=[];
 for(const [rid,r] of Object.entries(d.requirement_results||{}))for(const i of r.issues||[])if(!seen.has(i.iid)){seen.add(i.iid);out.push(i)}
 for(const i of (d.set_result||{}).issues||[])if(!seen.has(i.iid)){seen.add(i.iid);out.push(i)}
 const o={critical:0,major:1,minor:2};return out.filter(i=>i.status!=='rejected').sort((a,b)=>(o[a.severity]??3)-(o[b.severity]??3))}

function countUp(el,to){const d=600,s=performance.now();const f=t=>{const p=Math.min(1,(t-s)/d);el.textContent=Math.round(to*(1-Math.pow(1-p,3)));if(p<1)requestAnimationFrame(f)};requestAnimationFrame(f)}

function render(d){
 const iss=allIssues(d);d._iss=iss;const by=k=>iss.filter(i=>i.severity===k).length;
 const v=d.verdict||'';const bad=/^\s*НЕТ/i.test(v),warn=/услов|частич|с оговор/i.test(v);
 const vc=bad?'var(--crit)':warn?'var(--major)':'var(--ok)',vb=bad?'var(--crit-bg)':warn?'var(--major-bg)':'var(--ok-bg)';
 $('verdict').style.setProperty('--vc',vc);$('verdict').style.setProperty('--vbg',vb);
 setMood($('vm'),bad?'sad':'happy');setMood($('hero-m'),bad?'sad':'happy');say(bad?'Нашла '+iss.length+' замечаний. Давайте исправлять!':'Документ в отличной форме!',6000);if(0)$('vicon').innerHTML=bad?'<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"><path d="M18 6 6 18M6 6l12 12"/></svg>':'<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12 5 5 9-10"/></svg>';
 $('vtext').textContent=v;const run=d.run||{};
 $('vmeta').textContent=[run.document_title||run.document_name,run.model].filter(Boolean).join(' · ');
 const K=[['Требований',(d.requirements||[]).length,'',()=>showTab('rq')],['Критичных',by('critical'),'var(--crit)',()=>goIssues({sev:'critical'})],
  ['Существенных',by('major'),'var(--major)',()=>goIssues({sev:'major'})],['Незначительных',by('minor'),'var(--minor)',()=>goIssues({sev:'minor'})],
  ['Замечаний линтера',(d.lint||[]).length,'var(--faint)',()=>showTab('full')]];
 $('kpis').innerHTML='';K.forEach(([l,n,c,fn])=>{const e=document.createElement('div');e.className='card kpi';
  e.innerHTML=`<span>${c?`<i class="sw" style="background:${c}"></i>`:''}${l}</span><b>0</b>`;e.onclick=fn;$('kpis').append(e);countUp(e.querySelector('b'),n)});
 $('cIs').textContent=iss.length;$('cRq').textContent=(d.requirements||[]).length;
 const rv=d.review||{};$('sum').textContent=rv.summary||'—';
 $('prio').innerHTML=(rv.priorities||[]).map(p=>`<li><div>${esc(p.text)}<div>${(p.issues||[]).map(x=>`<span class="ref" data-iid="${esc(x)}">${esc(x)}</span>`).join('')}</div></div></li>`).join('')||'<li>—</li>';
 const cc={};for(const r of Object.values(d.requirement_results||{}))for(const [k,s] of Object.entries(r.criteria||{}))if(s==='violation')cc[k]=(cc[k]||0)+1;
 const rows=Object.entries(cc).sort((a,b)=>b[1]-a[1]),mx=Math.max(1,...rows.map(r=>r[1]));
 $('crit').innerHTML=rows.map(([k,n])=>`<div class="crit-row" data-crit="${esc(k)}"><span class="cn">${esc(CRIT[k]||k)}</span><span class="cb"><i style="width:0" data-w="${n/mx*100}"></i></span><b>${n}</b></div>`).join('')||'<p class="summary">Нарушений по отдельным требованиям нет.</p>';
 requestAnimationFrame(()=>document.querySelectorAll('.crit-row i').forEach(i=>i.style.width=i.dataset.w+'%'));
 const SL={ok:'Выполнено',violation:'Нарушено',unconfirmed:'Не подтверждено'};
 $('setc').innerHTML=Object.entries((d.set_result||{}).criteria||{}).map(([k,c])=>`<div class="setc"><span class="st ${esc(c.status)}">${SL[c.status]||esc(c.status)}</span><div class="tx"><b>${esc(CRIT[k]||k)}</b><span>${esc(c.comment)}</span></div></div>`).join('');
 const cnt={};iss.forEach(i=>(i.req_ids||[]).forEach(r=>(cnt[r]=cnt[r]||{critical:0,major:0,minor:0})[i.severity]++));
 $('reqs').innerHTML=(d.requirements||[]).map(r=>{const c=cnt[r.rid]||{};const dots=['critical','major','minor'].filter(k=>c[k]).map(k=>`<i class="${SEV[k][1]}" style="background:var(--sbg);color:var(--sc)">${c[k]}</i>`).join('')||'<span class="st ok">OK</span>';
  return `<tr class="rq" data-rid="${esc(r.rid)}"><td class="rid">${esc(r.rid)}</td><td>${esc(r.quote||r.summary)}</td><td style="color:var(--muted);font-size:12.5px">${esc(r.section)}</td><td><div class="dots">${dots}</div></td></tr>`}).join('');
 F={sev:'all',q:'',rid:null,crit:null};$('q').value='';drawIssues();showTab('ov')}

function drawIssues(){const iss=(DATA&&DATA._iss)||[];
 const base=iss.filter(i=>(!F.rid||(i.req_ids||[]).includes(F.rid))&&(!F.crit||i.criterion===F.crit)&&(!F.q||(i.problem+' '+i.fix+' '+(i.locations||[]).map(l=>l.quote).join(' ')+' '+i.iid).toLowerCase().includes(F.q)));
 const n=k=>k==='all'?base.length:base.filter(i=>i.severity===k).length;
 $('sev').innerHTML=['all','critical','major','minor'].map(k=>`<button data-s="${k}" class="${F.sev===k?'on':''}">${k==='all'?'Все':`<i class="sw" style="background:${SEV[k][2]}"></i>`+SEV[k][0]} <span style="color:var(--faint)">${n(k)}</span></button>`).join('');
 const tag=F.rid?'Требование '+F.rid:F.crit?'Критерий: '+(CRIT[F.crit]||F.crit):'';$('ftag').classList.toggle('on',!!tag);$('ftagText').textContent=tag;
 const list=base.filter(i=>F.sev==='all'||i.severity===F.sev);
 $('issues').innerHTML=list.map((i,ix)=>{const s=SEV[i.severity]||['—','sev-minor'];const loc=(i.locations||[])[0];
  const where=i.scope==='set'?'Набор требований':(i.req_ids||[]).join(', ');
  return `<details class="card issue ${s[1]}" id="is-${esc(i.iid)}" ${ix<1&&list.length<4?'open':''}><summary><span class="sev">${s[0]}</span><div class="ttl">${esc(i.problem)}<small>${esc(i.iid)} · ${esc(CRIT[i.criterion]||i.criterion)} · ${esc(where)}</small></div>
   <svg class="chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m6 9 6 6 6-6"/></svg></summary>
   <div class="body">${(i.locations||[]).filter(l=>l.quote).map(l=>`<div class="q"><span>Строка ${l.line_start}${l.line_end&&l.line_end!==l.line_start?'–'+l.line_end:''}</span>«${esc(l.quote)}»</div>`).join('')}
   ${i.fix?`<div class="fix"><b>Как исправить</b><span>${esc(i.fix)}</span></div>`:''}</div></details>`}).join('')||'<div class="empty">Под фильтр ничего не попало.</div>'}

function showTab(t){document.querySelectorAll('.tab').forEach(b=>b.classList.toggle('on',b.dataset.t===t));document.querySelectorAll('.pane').forEach(p=>p.classList.toggle('hidden',p.id!=='t-'+t))}
function goIssues(f){Object.assign(F,{sev:'all',rid:null,crit:null},f);drawIssues();showTab('is');$('tabs').scrollIntoView({behavior:'smooth'})}
$('tabs').onclick=e=>{const b=e.target.closest('.tab');if(b)showTab(b.dataset.t)};
$('sev').onclick=e=>{const b=e.target.closest('button');if(b){F.sev=b.dataset.s;drawIssues()}};
$('q').oninput=e=>{F.q=e.target.value.trim().toLowerCase();drawIssues()};
$('ftagX').onclick=()=>{F.rid=null;F.crit=null;drawIssues()};
$('reqs').onclick=e=>{const r=e.target.closest('tr.rq');if(r)goIssues({rid:r.dataset.rid})};
$('crit').onclick=e=>{const r=e.target.closest('.crit-row');if(r)goIssues({crit:r.dataset.crit})};
$('prio').onclick=e=>{const r=e.target.closest('.ref');if(!r)return;goIssues({});setTimeout(()=>{const el=$('is-'+r.dataset.iid);if(el){el.open=true;el.scrollIntoView({behavior:'smooth',block:'center'})}},50)};
renderSteps(0);
if('serviceWorker' in navigator&&(location.protocol==='https:'||location.hostname==='localhost'||location.hostname==='127.0.0.1'))navigator.serviceWorker.register('/sw.js').catch(()=>{});
/* ---- маскот Manana ---- */
let mid=0;
function mascotSVG(){const i='m'+(mid++);return `<svg viewBox="0 0 200 200" aria-hidden="true">
<defs><linearGradient id="${i}b" x1="0" y1="0" x2=".3" y2="1"><stop offset="0" stop-color="#2cc488"/><stop offset=".55" stop-color="#11895a"/><stop offset="1" stop-color="#0a6b45"/></linearGradient>
<radialGradient id="${i}e" cx=".5" cy=".7" r=".75"><stop offset="0" stop-color="#5ff0bd"/><stop offset=".45" stop-color="#138a5c"/><stop offset="1" stop-color="#05261a"/></radialGradient></defs>
<ellipse class="m-shadow" cx="100" cy="188" rx="46" ry="7" fill="#000" opacity=".2"/>
<g class="m-bob">
 <g class="m-sprout"><path d="M100 50V26" stroke="#b8901c" stroke-width="5" stroke-linecap="round"/><path d="M100 30C88 14 72 17 70 26c11 8 22 8 30 4z" fill="#e8c446"/><path d="M100 27c9-16 26-15 30-7-10 9-21 10-30 7z" fill="#c9a227"/></g>
 <g class="m-arm-l"><ellipse cx="42" cy="132" rx="13" ry="19" fill="#0f7d52" transform="rotate(28 42 132)"/></g>
 <g class="m-arm-r"><ellipse cx="158" cy="132" rx="13" ry="19" fill="#0f7d52" transform="rotate(-28 158 132)"/></g>
 <path d="M100 46c44 0 68 28 68 68 0 40-30 64-68 64s-68-24-68-64c0-40 24-68 68-68z" fill="url(#${i}b)" stroke="#c9a227" stroke-width="4"/>
 <ellipse cx="76" cy="66" rx="20" ry="9" fill="#fff" opacity=".22" transform="rotate(-20 76 66)"/>
 <ellipse cx="100" cy="150" rx="40" ry="22" fill="#fff" opacity=".1"/>
 <path d="M88 160v-13l12 9 12-9v13" fill="none" stroke="#f1d25e" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round"/>
 <g transform="translate(74 110)"><g class="m-lid"><ellipse rx="16" ry="20" fill="#05261a"/><g class="m-look"><ellipse cy="2" rx="12" ry="15" fill="url(#${i}e)"/><circle cx="-4" cy="-6" r="5" fill="#fff"/><circle cx="5" cy="7" r="2.2" fill="#fff" opacity=".9"/></g></g></g>
 <g transform="translate(126 110)"><g class="m-lid"><ellipse rx="16" ry="20" fill="#05261a"/><g class="m-look"><ellipse cy="2" rx="12" ry="15" fill="url(#${i}e)"/><circle cx="-4" cy="-6" r="5" fill="#fff"/><circle cx="5" cy="7" r="2.2" fill="#fff" opacity=".9"/></g></g></g>
 <ellipse cx="56" cy="134" rx="10" ry="5" fill="#ff8fa3" opacity=".6"/><ellipse cx="144" cy="134" rx="10" ry="5" fill="#ff8fa3" opacity=".6"/>
 <path class="m-mouth" d="M91 133q9 9 18 0" fill="none" stroke="#05261a" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
 <path class="m-sweat" d="M160 72c4 7 7 11 7 15a7 7 0 0 1-14 0c0-4 3-8 7-15z" fill="#8fd3ff"/>
 <g class="m-dots" fill="#f1d25e"><circle cx="150" cy="44" r="5"/><circle cx="166" cy="34" r="5"/><circle cx="182" cy="24" r="5"/></g>
 <g class="m-tool"><circle cx="164" cy="112" r="15" fill="rgba(255,255,255,.35)" stroke="#c9a227" stroke-width="5"/><path d="M175 124l14 14" stroke="#c9a227" stroke-width="7" stroke-linecap="round"/></g>
 <g class="m-spark" fill="#f1d25e"><path d="M30 50l4 10 10 4-10 4-4 10-4-10-10-4 10-4z"/><path d="M172 40l3 7 7 3-7 3-3 7-3-7-7-3 7-3z"/><path d="M180 150l3 6 6 3-6 3-3 6-3-6-6-3 6-3z"/></g>
</g></svg>`}
const MOUTH={idle:'M91 133q9 9 18 0',work:'M95 135q5-4 10 0',happy:'M88 129q12 20 24 0z',sad:'M91 138q9-9 18 0'};
function setMood(el,m){if(!el)return;el.classList.remove('work','happy','sad');if(m!=='idle')el.classList.add(m);
 const p=el.querySelector('.m-mouth');p.setAttribute('d',MOUTH[m]||MOUTH.idle);p.setAttribute('fill',m==='happy'?'#05261a':'none')}
document.querySelectorAll('.mascot').forEach(el=>{el.innerHTML=mascotSVG();setMood(el,el.classList.contains('work')?'work':'idle')});
const looks=[...document.querySelectorAll('.m-look')];
let mx=innerWidth/2,my=innerHeight/2,raf=0;
/* ---- чат с Manana ---- */
let RUN=null,CHAT=[],busy=false;
const md=t=>{let h=esc(t).replace(/\*\*(.+?)\*\*/g,'<b>$1</b>').replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\b(V-\d{3})\b/g,'<span class="iid" data-iid="$1">$1</span>');
 const out=[];let ul=false;for(const line of h.split('\n')){const m=line.match(/^\s*(?:[-*•]|\d+[.)])\s+(.*)/);
  if(m){if(!ul){out.push('<ul>');ul=true}out.push('<li>'+m[1]+'</li>')}else{if(ul){out.push('</ul>');ul=false}if(line.trim())out.push('<p>'+line+'</p>')}}
 if(ul)out.push('</ul>');return out.join('')};
function addMsg(role,text,cls=''){const d=document.createElement('div');d.className='msg '+(role==='user'?'me':'bot')+(cls?' '+cls:'');
 d.innerHTML=role==='user'?esc(text).replace(/\n/g,'<br>'):md(text);$('msgs').append(d);$('msgs').scrollTop=1e9;return d}
function suggestions(){const s=RUN?['Что исправить в первую очередь?','Объясни самое критичное замечание','Перепиши требование Ф-3 правильно','Почему вердикт такой?']
 :['Что ты умеешь?','Как написать хорошее требование?','Что такое ISO 29148?','Проверь формулировку: «Система должна работать быстро»'];
 $('sugg').innerHTML=s.map(x=>`<button>${esc(x)}</button>`).join('')}
function greet(){$('msgs').innerHTML='';CHAT=[];
 addMsg('bot',RUN?'Я закончила проверку и всё помню. Спросите про любое замечание, требование или что исправлять первым — объясню простыми словами.'
  :'Привет! Я **Manana** — ИИ-агент, который ищет ошибки в требованиях до начала разработки. Загрузите документ или спросите меня о чём-нибудь.');suggestions()}
function openChat(){document.body.classList.add('chat-open');setTimeout(()=>$('ci').focus(),250);if(!$('msgs').children.length)greet()}
function closeChat(){document.body.classList.remove('chat-open')}
async function send(text){text=(text||'').trim();if(!text||busy)return;busy=true;$('cs').disabled=true;$('ci').value='';$('ci').style.height='';
 addMsg('user',text);CHAT.push({role:'user',text});$('sugg').innerHTML='';
 const t=addMsg('bot','');t.innerHTML='<span class="typing"><i></i><i></i><i></i></span>';setMood($('chat-m'),'work');$('chatState').textContent='думаю…';
 try{const r=await fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:CHAT,run:RUN})});
  const j=await r.json();if(!r.ok)throw new Error(j.error||'Ошибка');
  t.innerHTML=md(j.reply);CHAT.push({role:'bot',text:j.reply});setMood($('chat-m'),'happy');setTimeout(()=>setMood($('chat-m'),'idle'),1800)}
 catch(e){t.classList.add('err');t.textContent='Не получилось ответить: '+e.message;CHAT.pop();setMood($('chat-m'),'sad');setTimeout(()=>setMood($('chat-m'),'idle'),2500)}
 busy=false;$('cs').disabled=false;$('chatState').textContent='на связи · ИИ-агент';$('msgs').scrollTop=1e9;suggestions()}
$('fab').onclick=openChat;$('chatClose').onclick=closeChat;$('chatReset').onclick=greet;
$('cs').onclick=()=>send($('ci').value);
$('ci').addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send($('ci').value)}});
$('ci').addEventListener('input',e=>{e.target.style.height='';e.target.style.height=Math.min(120,e.target.scrollHeight)+'px'});
$('sugg').onclick=e=>{const b=e.target.closest('button');if(b)send(b.textContent)};
$('msgs').onclick=e=>{const r=e.target.closest('.iid');if(!r||!DATA)return;goIssues({});setTimeout(()=>{const el=$('is-'+r.dataset.iid);if(el){el.open=true;el.scrollIntoView({behavior:'smooth',block:'center'})}},60)};
addEventListener('keydown',e=>{if(e.key==='Escape')closeChat()});
addEventListener('pointermove',e=>{mx=e.clientX;my=e.clientY;if(!raf)raf=requestAnimationFrame(()=>{raf=0;
 looks.forEach(g=>{const r=g.parentNode.getBoundingClientRect();if(!r.width)return;const dx=mx-(r.left+r.width/2),dy=my-(r.top+r.height/2),d=Math.hypot(dx,dy)||1,k=Math.min(1,d/220);
  g.setAttribute('transform',`translate(${(dx/d*4*k).toFixed(1)} ${(dy/d*5*k).toFixed(1)})`)})})});
(function blink(){setTimeout(()=>{document.querySelectorAll('.mascot').forEach(m=>m.classList.add('blink'));
 setTimeout(()=>document.querySelectorAll('.mascot').forEach(m=>m.classList.remove('blink')),130);blink()},2200+Math.random()*3200)})();
let bubT;function say(t,ms=3500){const b=$('bub');if(!b)return;b.textContent=t;b.classList.add('on');clearTimeout(bubT);bubT=setTimeout(()=>b.classList.remove('on'),ms)}
const LINES=['Привет! Я Manana 🌱','Перетащите документ — я найду, где требования хромают','Проверяю по ISO 29148 и IEEE 830','Нет файла под рукой? Нажмите «Пример»','Каждое замечание — с цитатой и исправлением'];let li=0;
document.querySelectorAll('.mascot').forEach(m=>m.addEventListener('click',()=>{m.classList.remove('jump');void m.offsetWidth;m.classList.add('jump');
 if(m.id==='hero-m'){say(li%2?'Напишите мне — я отвечу!':LINES[li%LINES.length]);li++;if(li>1)setTimeout(openChat,700)}}));
setTimeout(()=>{$('hero-m').classList.add('wave');say(LINES[0]);setTimeout(()=>$('hero-m').classList.remove('wave'),1600)},700);
['dragenter'].forEach(t=>$('drop').addEventListener(t,()=>{setMood($('hero-m'),'happy');say('Бросайте сюда!',1500)}));
$('drop').addEventListener('dragleave',()=>setMood($('hero-m'),'idle'));
</script></body></html>"""



MANIFEST = """{
  "name": "Manana — проверка требований",
  "short_name": "Manana",
  "description": "ИИ-агент, который находит ошибки в требованиях до начала разработки",
  "start_url": "/",
  "scope": "/",
  "display": "standalone",
  "orientation": "portrait",
  "background_color": "#0b1310",
  "theme_color": "#0a6b45",
  "lang": "ru",
  "icons": [
    {"src": "/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any maskable"},
    {"src": "/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}
  ]
}"""

# Сеть в приоритете: проверка требований без сети невозможна, кэш нужен только чтобы показать понятную заглушку.
SERVICE_WORKER = r"""
const C='manana-v1';
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(['/icon-192.png'])).catch(()=>{}));self.skipWaiting()});
self.addEventListener('activate',e=>e.waitUntil(self.clients.claim()));
self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET'||e.request.mode!=='navigate')return;
  e.respondWith(fetch(e.request).catch(()=>new Response(
    '<!doctype html><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">'+
    '<body style="font:16px -apple-system,sans-serif;background:#0b1310;color:#e6eee8;display:grid;place-items:center;height:100vh;margin:0;text-align:center">'+
    '<div><img src="/icon-192.png" width=96 style="border-radius:22px"><h2>Manana не на связи</h2><p>Проверьте интернет и попробуйте снова.</p></div>',
    {headers:{'Content-Type':'text/html; charset=utf-8'}})));
});
"""

LOGIN_PAGE = r"""<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover"><title>Manana — вход</title>
<link rel="icon" href="{{FAVICON}}"><link rel="manifest" href="/manifest.webmanifest"><meta name="theme-color" content="#0a6b45">
<link rel="apple-touch-icon" href="/apple-touch-icon.png"><meta name="apple-mobile-web-app-capable" content="yes">
<style>
*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;padding:24px;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
background:radial-gradient(900px 400px at 80% -10%,rgba(201,162,39,.2),transparent 60%),linear-gradient(160deg,#063d28,#0a6b45 70%,#0e8a5a);color:#13201a}
.card{width:100%;max-width:360px;background:#fff;border-radius:22px;padding:28px 24px;box-shadow:0 30px 60px rgba(0,0,0,.3);text-align:center}
img{width:96px;height:96px;border-radius:24px;margin:-76px auto 8px;display:block;box-shadow:0 12px 24px rgba(0,0,0,.25)}
h1{font-size:22px;margin:6px 0 4px}p{color:#5f6e66;margin:0 0 18px;font-size:14px}
input{width:100%;padding:13px 14px;border:1px solid #e2e8e3;border-radius:12px;font-size:16px;outline:0}input:focus{border-color:#0a6b45}
button{width:100%;margin-top:12px;padding:13px;border:0;border-radius:12px;background:linear-gradient(180deg,#0e8a5a,#0a6b45);color:#fff;font-weight:600;font-size:15px;cursor:pointer}
.err{color:#c62828;font-size:13px;min-height:18px;margin-top:10px}
</style></head><body><form class="card" method="post" action="/login">
<img src="/icon-192.png" alt=""><h1>Manana</h1><p>ИИ-агент проверки требований. Введите пароль, чтобы войти.</p>
<input type="password" name="password" placeholder="Пароль" autocomplete="current-password" autofocus required>
<button type="submit">Войти</button><div class="err">{{ERR}}</div></form></body></html>"""
