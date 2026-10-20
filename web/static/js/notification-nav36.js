/* Navigation follows canonical own identity; it never grants API authority. */
(()=>{'use strict';let dead=false;const links=()=>document.querySelectorAll('[data-notification-nav]');function clear(){dead=true;for(const link of links())link.hidden=true;}
 for(const event of['metodobase-session-changed','pagehide'])window.addEventListener(event,clear);
 async function start(){try{await Api.session.ready;const fence=Api.session.capture(),me=await SessionIdentity.ready;Api.session.check(fence);if(dead||!me)return;const owner=me.tipo==='gym'&&me.role==='owner'&&!me.team_gym_id,personal=['admin','nutriologo','viewer'].includes(me.role)&&(me.tipo==='usuario'||!!me.team_gym_id);for(const link of links())link.hidden=!(link.dataset.notificationNav==='gym'?owner:personal);}catch{for(const link of links())link.hidden=true;}}
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();})();
