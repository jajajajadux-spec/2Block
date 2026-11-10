import test from 'node:test';
import assert from 'node:assert/strict';
import {cameraRay, lookAt, multiply, perspective, rayBox} from '../apps/web/game/math.js';

test('camera target projects to the center in perspective',()=>{
  const eye=[6,5,8],target=[1,1,2],m=multiply(perspective(16/9),lookAt(eye,target));
  const point=[...target,1];
  const clip=Array.from({length:4},(_,r)=>point.reduce((sum,v,c)=>sum+m[c*4+r]*v,0));
  assert.ok(Math.abs(clip[0]/clip[3])<1e-6);
  assert.ok(Math.abs(clip[1]/clip[3])<1e-6);
  assert.ok(clip[3]>0);
});
test('center ray points from camera toward target',()=>{
  const ray=cameraRay([0,0,5],[0,0,0],0,0,1);
  assert.deepEqual(ray,[0,0,-1]);
  assert.ok(cameraRay([0,0,5],[0,0,0],1,0,1)[0]>0);
});
test('ray returns the correct surface for adjacent block placement',()=>{
  assert.deepEqual(rayBox([0,2,0],[0,-1,0],[-.5,0,-.5],[.5,1,.5]),{distance:1,normal:[0,1,0]});
  assert.equal(rayBox([2,2,0],[0,-1,0],[-.5,0,-.5],[.5,1,.5]),null);
  assert.equal(rayBox([0,2,0],[0,1,0],[-.5,0,-.5],[.5,1,.5]),null);
});
