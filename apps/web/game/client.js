import {Renderer} from './renderer.js';
import {clamp} from './math.js';

const $=selector=>document.querySelector(selector);
const canvas=$('#world'), welcome=$('#welcome'), pause=$('#pause');
const keys=new Set(), actions=[], labels=new Map(), displayed=new Map();
let renderer, token, playerId, world, connected=false, jump=false, tool='walk';
let yaw=.65, pitch=.48, distance=8, eye=[0,5,8], target=[0,1,0];
let pointer={nx:0,ny:0}, dragging=null, lastFrame=performance.now(), toastTimer;
let join={gameId:'block-yard',user:'Guest',avatar:{body:'#58c9a5',head:'#f2c78f',hat:'none'}};

function toast(message) {
  $('#toast').textContent=message;$('#toast').hidden=false;
  clearTimeout(toastTimer);toastTimer=setTimeout(()=>{$('#toast').hidden=true;},3500);
}

async function api(path,body,auth=true) {
  const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json',
    ...(auth?{Authorization:`Bearer ${token}`}:{})},body:JSON.stringify(body),signal:AbortSignal.timeout(4000)});
  const data=await response.json();
  if(!response.ok) throw new Error(data.error || 'The server did not respond.');
  return data;
}

function receive(next) {
  const previous=world?.players.find(p=>p.id===playerId);
  world=next;renderer.setWorld(world);
  const me=world.players.find(p=>p.id===playerId);
  $('#connection').textContent=`${world.players.length} / 16 players · Connected`;
  $('#coin-count').textContent=`${me.coins} / ${world.coins.length} coins`;
  $('#checkpoint').textContent=`Checkpoint: ${me.checkpoint==='spawn'?'Spawn':'Golden steps'}`;
  if(previous && me.coins>previous.coins) toast(me.coins===world.coins.length?'All coins found. Nice work!':'+1 coin');
  if(previous && me.checkpoint!==previous.checkpoint) toast('Checkpoint saved! Press R to return here.');
  for(const p of world.players) {
    if(!displayed.has(p.id)) displayed.set(p.id,{...p});
    if(!labels.has(p.id)) {
      const label=document.createElement('span');label.className='nametag';
      $('#nametags').append(label);labels.set(p.id,label);
    }
    labels.get(p.id).textContent=p.user+(p.id===playerId?' (you)':'');
  }
  for(const [id,label] of labels) if(!world.players.some(p=>p.id===id)) {label.remove();labels.delete(id);displayed.delete(id);}
}

async function connect() {
  $('#reconnect').hidden=true;$('#start').disabled=true;
  try {
    const session=await api('/api/join',join,false);
    token=session.token;playerId=session.playerId;connected=true;
    delete join.launchId; // A reconnect creates a new guest session; tickets are one-use.
    receive(session.world);$('#start').disabled=false;$('#start').textContent="Let's play";
    if(!welcome.open) canvas.focus();
    network();
  } catch(error) {
    $('#welcome-text').textContent=error.message;
    $('#connection').textContent='Could not join';$('#reconnect').hidden=false;
  }
}

async function network() {
  while(connected) {
    const started=performance.now();
    try {
      const playing=!welcome.open && !pause.open && !document.hidden;
      const x=playing?(Number(keys.has('KeyD')||keys.has('ArrowRight'))-Number(keys.has('KeyA')||keys.has('ArrowLeft'))):0;
      const z=playing?(Number(keys.has('KeyS')||keys.has('ArrowDown'))-Number(keys.has('KeyW')||keys.has('ArrowUp'))):0;
      const scale=Math.max(1,Math.hypot(x,z));
      const payload={dx:(x*Math.cos(yaw)+z*Math.sin(yaw))/scale,
        dz:(-x*Math.sin(yaw)+z*Math.cos(yaw))/scale,
        jump:playing&&jump,sprint:playing&&(keys.has('ShiftLeft')||keys.has('ShiftRight'))};
      jump=false;
      receive(await api('/api/step',payload));
      const action=actions.shift();
      if(action) {
        try {receive(await api('/api/action',action));}
        catch(error) {toast(error.message);}
      }
    } catch(error) {
      connected=false;keys.clear();actions.length=0;
      $('#connection').textContent='Disconnected';$('#reconnect').hidden=false;
      $('#start').disabled=true;$('#start').textContent='Reconnect below';
      if(welcome.open) {welcome.close();}
      if(pause.open) pause.close();
      toast(error.message);break;
    }
    await new Promise(resolve=>setTimeout(resolve,Math.max(0,50-(performance.now()-started))));
  }
}

function selectTool(value) {
  tool=value;
  document.querySelectorAll('[data-tool]').forEach(button=>{
    const selected=button.dataset.tool===value;button.classList.toggle('selected',selected);button.setAttribute('aria-pressed',String(selected));
  });
  $('#hint').textContent=value==='walk'?'WASD to move · Space to jump · Right-drag to look · Scroll to zoom':
    value==='place'?'Click a nearby cell to place a block · Choose a color in the hotbar':'Click one of your blocks to remove it';
}

function enqueue(action) {if(connected && actions.length<4) actions.push(action);}
function setPause() {keys.clear();jump=false;if(!welcome.open && !pause.open) pause.showModal();}
$('#menu-button').onclick=setPause;
$('#start').onclick=()=>{welcome.close();canvas.focus();toast('Try jumping onto the steps. Your checkpoint saves when you reach the flag.');};
$('#resume').onclick=()=>{pause.close();canvas.focus();};
$('#respawn').onclick=()=>{enqueue({kind:'respawn'});pause.close();canvas.focus();};
$('#fullscreen').onclick=async()=>{try{if(document.fullscreenElement) await document.exitFullscreen();else await document.documentElement.requestFullscreen();}catch{toast('Fullscreen is unavailable in this browser.');}};
$('#wave').onclick=()=>{enqueue({kind:'wave'});canvas.focus();};
$('#rejoin').onclick=()=>{if(!connected) connect();};
document.querySelectorAll('[data-tool]').forEach(button=>button.onclick=()=>{selectTool(button.dataset.tool);canvas.focus();});
window.addEventListener('keydown',event=>{
  if(event.code==='Escape'){event.preventDefault();if(pause.open) {pause.close();canvas.focus();}else setPause();return;}
  if(welcome.open || pause.open || event.target.matches('input,button,summary')) return;
  if(['Space','ArrowUp','ArrowDown','ArrowLeft','ArrowRight'].includes(event.code)) event.preventDefault();
  if(event.code==='Space' && !event.repeat) jump=true;
  keys.add(event.code);
  if(event.code==='Digit1') selectTool('walk');
  if(event.code==='Digit2') selectTool('place');
  if(event.code==='Digit3') selectTool('remove');
  if(event.code==='Digit4' && !event.repeat) enqueue({kind:'wave'});
  if(event.code==='KeyR' && !event.repeat) enqueue({kind:'respawn'});
});
window.addEventListener('keyup',event=>keys.delete(event.code));
window.addEventListener('blur',()=>{keys.clear();jump=false;dragging=null;});
document.addEventListener('visibilitychange',()=>{keys.clear();jump=false;});
for(const button of document.querySelectorAll('[data-key]')) {
  button.onpointerdown=event=>{event.preventDefault();button.setPointerCapture(event.pointerId);keys.add(button.dataset.key);};
  button.onpointerup=button.onpointercancel=()=>keys.delete(button.dataset.key);
}
$('#touch-jump').onpointerdown=event=>{event.preventDefault();jump=true;};
canvas.oncontextmenu=event=>event.preventDefault();
canvas.onwheel=event=>{event.preventDefault();distance=clamp(distance+event.deltaY*.01,3,18);};
canvas.onpointerdown=event=>{
  canvas.focus();canvas.setPointerCapture(event.pointerId);
  dragging={x:event.clientX,y:event.clientY,orbit:event.button===2||(event.pointerType==='touch'&&tool==='walk'),moved:false};
};
canvas.onpointermove=event=>{
  pointer={nx:event.clientX/canvas.clientWidth*2-1,ny:1-event.clientY/canvas.clientHeight*2};
  if(dragging?.orbit) {
    const dx=event.clientX-dragging.x,dy=event.clientY-dragging.y;
    yaw-=dx*.007;pitch=clamp(pitch+dy*.006,.15,1.25);
    dragging.x=event.clientX;dragging.y=event.clientY;dragging.moved=true;
  }
};
canvas.onpointerup=event=>{
  const orbit=dragging?.orbit;dragging=null;
  if(orbit || event.button!==0 || tool==='walk' || !connected) return;
  pointer={nx:event.clientX/canvas.clientWidth*2-1,ny:1-event.clientY/canvas.clientHeight*2};
  const pick=renderer.pick(eye,target,pointer.nx,pointer.ny),cell=pick?.[tool];
  if(cell) enqueue({kind:tool,x:cell.x,y:cell.y,z:cell.z,color:$('#block-color').value});
};
canvas.onpointercancel=()=>{dragging=null;};

function frame(now) {
  const dt=Math.min((now-lastFrame)/1000,.1);lastFrame=now;
  if(!pause.open && !welcome.open) yaw+=(Number(keys.has('KeyQ'))-Number(keys.has('KeyE')))*dt*1.8;
  if(world) {
    for(const p of world.players) {
      const d=displayed.get(p.id),gap=Math.hypot(d.x-p.x,d.y-p.y,d.z-p.z);
      const blend=gap>3?1:1-Math.exp(-dt*22);
      const moving=Math.hypot(d.x-p.x,d.z-p.z)>.015;
      for(const axis of ['x','y','z']) d[axis]+=(p[axis]-d[axis])*blend;
      d.yaw+=Math.atan2(Math.sin(p.yaw-d.yaw),Math.cos(p.yaw-d.yaw))*blend;
      Object.assign(d,{avatar:p.avatar,grounded:p.grounded,waving:p.waving,moving});
    }
    const me=displayed.get(playerId), own=world.players.find(p=>p.id===playerId);
    target=[me.x,me.y+1,me.z];
    eye=[target[0]+Math.sin(yaw)*Math.cos(pitch)*distance,target[1]+Math.sin(pitch)*distance,target[2]+Math.cos(yaw)*Math.cos(pitch)*distance];
    // Shorten the orbit before a wall rather than letting the camera enter it.
    const ray=target.map((v,i)=>(eye[i]-v)/distance);
    let cameraDistance=distance;
    for(const block of world.blocks) {
      const hit=renderer.pickCamera(target,ray,block);
      if(hit) cameraDistance=Math.min(cameraDistance,Math.max(.7,hit.distance-.25));
    }
    eye=target.map((v,i)=>v+ray[i]*cameraDistance);
    const pick=tool==='walk'?null:renderer.pick(eye,target,pointer.nx,pointer.ny);
    const cell=pick?.[tool];
    const preview=cell&&Math.hypot(cell.x-own.x,cell.y-own.y,cell.z-own.z)<=5?
      {...cell,color:tool==='remove'?'#ff8d79':$('#block-color').value}:null;
    renderer.render(eye,target,[...displayed.values()],own,now/1000,preview);
    for(const p of displayed.values()) {
      const point=renderer.screen([p.x,p.y+2.6,p.z]),label=labels.get(p.id);
      label.hidden=!point;
      if(point) label.style.transform=`translate(${point[0]}px,${point[1]}px) translate(-50%,-100%)`;
    }
  }
  requestAnimationFrame(frame);
}

function leave() {
  connected=false;
  if(token) fetch('/api/leave',{method:'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${token}`},body:'{}',keepalive:true}).catch(()=>{});
}
window.addEventListener('pagehide',leave);

try {
  const fragment=location.hash.slice(1);
  const gameId=new URLSearchParams(location.search).get('gameId') || 'block-yard';
  history.replaceState(null,'','/play');
  if(fragment) join=JSON.parse(decodeURIComponent(fragment));
  else {join.gameId=gameId;try{const saved=JSON.parse(localStorage.getItem('twoblock.guest.v1'));if(saved) Object.assign(join,saved);}catch{}}
  if(!['block-yard','sunset-steps'].includes(join.gameId)) throw new Error('Unknown game. Choose a game from the hub.');
  history.replaceState(null,'','/play?gameId='+encodeURIComponent(join.gameId));
  $('#room-title').textContent=join.gameId==='block-yard'?'Block Yard':'Sunset Steps';
  renderer=new Renderer(canvas);
  canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();connected=false;toast('Graphics context lost. Reload to reconnect.');$('#reconnect').hidden=false;});
  canvas.addEventListener('webglcontextrestored',()=>location.reload());
  welcome.showModal();requestAnimationFrame(frame);connect();
} catch(error) {$('#welcome-text').textContent=error.message;$('#start').textContent='Unable to start';welcome.showModal();}
