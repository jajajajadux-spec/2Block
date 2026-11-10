import {cameraRay, lookAt, multiply, perspective, rayBox} from './math.js';

const VERTEX = `attribute vec3 position; attribute vec3 color; attribute vec3 normal;
uniform mat4 viewProjection; varying vec3 tint; varying float fog;
void main(){ vec4 p=viewProjection*vec4(position,1.0); gl_Position=p;
float light=0.55+0.45*max(dot(normal,normalize(vec3(-0.4,0.9,0.5))),0.0);
tint=color*light; fog=clamp((p.w-22.0)/65.0,0.0,0.8); }`;
const FRAGMENT = `precision mediump float; varying vec3 tint; varying float fog;
uniform float alpha; void main(){gl_FragColor=vec4(mix(tint,vec3(0.65,0.82,0.92),fog),alpha);}`;
const FACES = [
  [[0,1,0], [[-1,1,-1],[-1,1,1],[1,1,1],[1,1,-1]]],
  [[0,-1,0], [[-1,-1,1],[-1,-1,-1],[1,-1,-1],[1,-1,1]]],
  [[0,0,1], [[-1,-1,1],[1,-1,1],[1,1,1],[-1,1,1]]],
  [[0,0,-1], [[1,-1,-1],[-1,-1,-1],[-1,1,-1],[1,1,-1]]],
  [[1,0,0], [[1,-1,1],[1,-1,-1],[1,1,-1],[1,1,1]]],
  [[-1,0,0], [[-1,-1,-1],[-1,-1,1],[-1,1,1],[-1,1,-1]]],
];
function rgb(hex) { return [1,3,5].map(i => parseInt(hex.slice(i,i+2),16)/255); }

function box(vertices, x,y,z, sx,sy,sz, color, yaw=0, pivot=null) {
  const tint=rgb(color), c=Math.cos(yaw), s=Math.sin(yaw);
  for (const [normal, corners] of FACES) for (const index of [0,1,2,0,2,3]) {
    const corner=corners[index];
    let px=x+corner[0]*sx/2, pz=z+corner[2]*sz/2;
    if (pivot) { const lx=px-pivot[0], lz=pz-pivot[1]; px=pivot[0]+lx*c+lz*s; pz=pivot[1]-lx*s+lz*c; }
    vertices.push(px,y+corner[1]*sy/2,pz, ...tint,
      normal[0]*c+normal[2]*s,normal[1],-normal[0]*s+normal[2]*c);
  }
}

export class Renderer {
  constructor(canvas) {
    this.canvas=canvas;
    const gl=this.gl=canvas.getContext('webgl', {antialias:true, alpha:false});
    if (!gl) throw new Error('Your browser could not start WebGL. Enable hardware acceleration or try a different browser.');
    const shader=(type, source) => {
      const result=gl.createShader(type); gl.shaderSource(result,source); gl.compileShader(result);
      if (!gl.getShaderParameter(result,gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(result));
      return result;
    };
    const program=this.program=gl.createProgram();
    gl.attachShader(program,shader(gl.VERTEX_SHADER,VERTEX));
    gl.attachShader(program,shader(gl.FRAGMENT_SHADER,FRAGMENT)); gl.linkProgram(program);
    if (!gl.getProgramParameter(program,gl.LINK_STATUS)) throw new Error('Could not link the 3D shaders.');
    gl.useProgram(program);
    this.matrix=gl.getUniformLocation(program,'viewProjection');
    this.alpha=gl.getUniformLocation(program,'alpha');
    this.attributes=['position','color','normal'].map(name=>gl.getAttribLocation(program,name));
    this.staticBuffer=gl.createBuffer(); this.dynamicBuffer=gl.createBuffer();
    gl.enable(gl.DEPTH_TEST); gl.enable(gl.BLEND); gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);
    this.staticCount=0; this.signature='';
  }

  setWorld(world) {
    this.world=world;
    const signature=JSON.stringify(world.blocks);
    if (signature===this.signature) return;
    this.signature=signature;
    const vertices=[];
    for (let x=-16;x<16;x++) for (let z=-16;z<16;z++)
      box(vertices,x+.5,-.2,z+.5,1,.4,1,(x+z)%2 ? '#78ad84' : '#82b78e');
    for (const b of world.blocks) box(vertices,b.x,b.y+.5,b.z,1,1,1,b.color);
    for (const h of world.hazards) box(vertices,h.x,.015,h.z,h.width,.03,h.depth,'#f06b48');
    const gl=this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER,this.staticBuffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.STATIC_DRAW);
    this.staticCount=vertices.length/9;
  }

  draw(buffer,count) {
    const gl=this.gl;
    gl.bindBuffer(gl.ARRAY_BUFFER,buffer);
    this.attributes.forEach((attribute,i)=>{gl.enableVertexAttribArray(attribute);gl.vertexAttribPointer(attribute,3,gl.FLOAT,false,36,i*12);});
    gl.drawArrays(gl.TRIANGLES,0,count);
  }

  render(eye,target,players,me,time,preview) {
    const gl=this.gl, canvas=this.canvas, ratio=Math.min(devicePixelRatio || 1,2);
    const width=Math.round(canvas.clientWidth*ratio), height=Math.round(canvas.clientHeight*ratio);
    if (canvas.width!==width || canvas.height!==height) {canvas.width=width;canvas.height=height;}
    gl.viewport(0,0,width,height); gl.clearColor(.65,.82,.92,1);
    gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);
    this.viewProjection=multiply(perspective(width/height),lookAt(eye,target));
    gl.uniformMatrix4fv(this.matrix,false,this.viewProjection); gl.uniform1f(this.alpha,1);
    this.draw(this.staticBuffer,this.staticCount);
    const vertices=[];
    for (const p of players) {
      const bob=p.moving && p.grounded ? Math.sin(time*12)*.035 : 0;
      const b=(ox,oy,oz,sx,sy,sz,color)=>box(vertices,p.x+ox,p.y+oy+bob,p.z+oz,sx,sy,sz,color,p.yaw,[p.x,p.z]);
      const stride=p.moving ? Math.sin(time*12)*.12 : 0;
      b(-.18,.3,stride,.27,.6,.34,'#344f75'); b(.18,.3,-stride,.27,.6,.34,'#344f75');
      b(0,.95,0,.68,.7,.36,p.avatar.body);
      b(-.47,.95,-stride,.22,.65,.28,p.avatar.body);
      b(.47,p.waving ? 1.65+Math.sin(time*15)*.1 : .95,stride,.22,.65,.28,p.avatar.body);
      b(0,1.55,0,.5,.5,.5,p.avatar.head);
      b(-.11,1.6,.255,.055,.065,.02,'#253b46'); b(.11,1.6,.255,.055,.065,.02,'#253b46');
      if(p.avatar.hat!=='none') {b(0,1.84,0,.64,.09,.62,'#f2eee5');b(0,p.avatar.hat==='tall'?2.05:1.9,0,.46,p.avatar.hat==='tall'?.4:.1,.45,'#e6e5df');}
    }
    for(const coin of this.world?.coins || []) if(!me?.collected.includes(coin.id))
      box(vertices,coin.x,coin.y+Math.sin(time*3+Number(coin.id))*.12,coin.z,.26,.45,.26,'#ffd362',time*2,[coin.x,coin.z]);
    for(const point of this.world?.checkpoints || []) {
      box(vertices,point.x,point.y+.025,point.z,.95,.05,.95,me?.checkpoint===point.id?'#64e6b6':'#ffd362');
      if(point.id!=='spawn') {box(vertices,point.x+.3,point.y+1,point.z,.07,2,.07,'#f7eee0');box(vertices,point.x+.6,point.y+1.7,point.z,.6,.4,.08,'#ffd362');}
    }
    gl.bindBuffer(gl.ARRAY_BUFFER,this.dynamicBuffer);
    gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(vertices),gl.DYNAMIC_DRAW);
    this.draw(this.dynamicBuffer,vertices.length/9);
    if(preview) {
      const ghost=[]; box(ghost,preview.x,preview.y+.5,preview.z,1.02,1.02,1.02,preview.color);
      gl.uniform1f(this.alpha,.4);gl.depthMask(false);
      gl.bindBuffer(gl.ARRAY_BUFFER,this.dynamicBuffer);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(ghost),gl.DYNAMIC_DRAW);
      this.draw(this.dynamicBuffer,ghost.length/9);gl.depthMask(true);
    }
  }

  pick(eye,target,nx,ny) {
    const direction=cameraRay(eye,target,nx,ny,this.canvas.clientWidth/this.canvas.clientHeight);
    let closest=null;
    for(const block of this.world?.blocks || []) {
      const hit=rayBox(eye,direction,[block.x-.5,block.y,block.z-.5],[block.x+.5,block.y+1,block.z+.5]);
      if(hit && (!closest || hit.distance<closest.distance)) closest={...hit,block};
    }
    if(closest) {
      const b=closest.block,n=closest.normal;
      return {remove:b,place:{x:b.x+n[0],y:b.y+n[1],z:b.z+n[2]}};
    }
    const distance=-eye[1]/direction[1];
    if(distance>0 && distance<100) return {place:{x:Math.round(eye[0]+direction[0]*distance),y:0,z:Math.round(eye[2]+direction[2]*distance)}};
    return null;
  }

  pickCamera(origin,direction,block) {
    return rayBox(origin,direction,[block.x-.6,block.y-.1,block.z-.6],
      [block.x+.6,block.y+1.1,block.z+.6]);
  }

  screen(position) {
    const m=this.viewProjection;
    if(!m) return null;
    const [x,y,z]=position, w=m[3]*x+m[7]*y+m[11]*z+m[15];
    if(w<=0) return null;
    return [(1+(m[0]*x+m[4]*y+m[8]*z+m[12])/w)*this.canvas.clientWidth/2,
      (1-(m[1]*x+m[5]*y+m[9]*z+m[13])/w)*this.canvas.clientHeight/2];
  }
}
