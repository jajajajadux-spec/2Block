export const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
export const sub = (a, b) => a.map((v, i) => v - b[i]);
export const dot = (a, b) => a.reduce((n, v, i) => n + v * b[i], 0);
export const cross = (a, b) => [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]];
export function unit(v) { const length = Math.hypot(...v) || 1; return v.map(n => n / length); }

export function perspective(aspect, fov = Math.PI / 3, near = .1, far = 150) {
  const f = 1 / Math.tan(fov / 2), range = 1 / (near - far);
  return [f/aspect,0,0,0, 0,f,0,0, 0,0,(far+near)*range,-1, 0,0,2*far*near*range,0];
}

export function lookAt(eye, target) {
  const z = unit(sub(eye, target)), x = unit(cross([0,1,0], z)), y = cross(z, x);
  return [x[0],y[0],z[0],0, x[1],y[1],z[1],0, x[2],y[2],z[2],0,
    -dot(x,eye),-dot(y,eye),-dot(z,eye),1];
}

export function multiply(a, b) {
  const out = new Float32Array(16);
  for (let c=0;c<4;c++) for (let r=0;r<4;r++)
    for (let k=0;k<4;k++) out[c*4+r] += a[k*4+r]*b[c*4+k];
  return out;
}

export function cameraRay(eye, target, nx, ny, aspect) {
  const forward = unit(sub(target, eye)), right = unit(cross(forward,[0,1,0]));
  const up = cross(right, forward), scale = Math.tan(Math.PI / 6);
  return unit(forward.map((v,i) => v + right[i]*nx*aspect*scale + up[i]*ny*scale));
}

// Slab intersection also gives the face normal used to place an adjacent block.
export function rayBox(origin, direction, low, high) {
  let enter = -Infinity, exit = Infinity, normal = [0,0,0];
  for (let axis=0;axis<3;axis++) {
    if (Math.abs(direction[axis]) < 1e-8) {
      if (origin[axis] < low[axis] || origin[axis] > high[axis]) return null;
      continue;
    }
    let a = (low[axis]-origin[axis])/direction[axis];
    let b = (high[axis]-origin[axis])/direction[axis];
    const sign = direction[axis] > 0 ? -1 : 1;
    if (a>b) [a,b]=[b,a];
    if (a>enter) { enter=a; normal=[0,0,0]; normal[axis]=sign; }
    exit=Math.min(exit,b);
    if (enter>exit) return null;
  }
  return enter >= 0 && exit >= 0 ? {distance:enter, normal} : null;
}
