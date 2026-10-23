'use strict';
const {test} = require('node:test');
const assert = require('node:assert/strict');
const E = require('../js/snek-engine');
const C = require('../js/snek-controls');
const cfg = E.cloneConfig({});
const fresh = () => { const g = E.reset(cfg, [[2,2]], null); return g; };

for (const [name,start,dir,end] of [
  ['right',[39,10],[1,0],[0,10]],['left',[0,10],[-1,0],[39,10]],
  ['bottom',[10,29],[0,1],[10,0]],['top',[10,0],[0,-1],[10,29]]
]) test('wrap '+name+' keeps row/column, heading and one-cell cadence',()=>{
  const g=fresh();g.snake.positions=[start];g.snake.direction=dir;
  for(let i=0;i<1201;i++) {
    E.step(g,E.settings(cfg));
    if(i===0)assert.deepEqual(g.snake.positions[0],end);
    assert.equal(g.gameOver,false);assert.deepEqual(g.snake.direction,dir);
    assert.ok(g.snake.positions.every(([x,y])=>x>=0&&x<40&&y>=0&&y<30));
  }
  assert.equal(g.ticks,1201);assert.ok(!g.events.some(e=>e.type==='wall'));
});
test('wrapped food scores exactly once',()=>{
  const g=fresh();g.snake.positions=[[39,10]];g.food.position=[0,10];
  E.step(g,E.settings(cfg));E.step(g,E.settings(cfg));
  assert.equal(g.score,1);assert.equal(g.snake.length,2);
  assert.equal(g.events.filter(e=>e.type==='eat').length,1);
});
test('wrapped self collision is fatal',()=>{
  const g=fresh();g.snake.length=5;g.snake.positions=[[39,10],[39,9],[0,9],[0,10],[1,10]];
  E.step(g,E.settings(cfg));assert.equal(g.cause,'self');
});
test('wrapped poop collision is fatal',()=>{
  const g=fresh();g.snake.positions=[[39,10]];g.poops=[{position:[0,10]}];
  E.step(g,E.settings(cfg,{wonqMode:true}));assert.equal(g.cause,'poop');
});
test('vacated tail across seam is legal and body remains in bounds',()=>{
  const g=fresh();g.snake.length=4;g.snake.positions=[[39,10],[39,9],[0,9],[0,10]];
  E.step(g,E.settings(cfg));assert.equal(g.gameOver,false);
  assert.deepEqual(g.snake.positions,[[0,10],[39,10],[39,9],[0,9]]);
});
test('two WoNQ cycles span seam: actual meals only, one tail poop each fifth',()=>{
  const g=fresh();g.snake.positions=[[35,15]];
  const s=E.settings(cfg,{wonqMode:true});
  assert.equal(g.shitCounter,0);
  for(let i=1;i<=10;i++) {
    const [x,y]=g.snake.positions[0];g.food.position=[(x+1)%40,y];E.step(g,s);
    assert.equal(g.score,i);assert.equal(g.shitCounter,i%5);assert.equal(g.poops.length,Math.floor(i/5));
    assert.equal(g.gameOver,false);
    if(i%5===0)assert.deepEqual(g.poops.at(-1).position,g.snake.positions.at(-1));
    assert.ok(!g.snake.positions.some(p=>String(p)===String(g.food.position)));
    assert.ok(!g.poops.some(p=>String(p.position)===String(g.food.position)));
  }
  g.food.position=[3,2];E.step(g,s);assert.equal(g.shitCounter,0);assert.equal(g.poops.length,2);
});
test('Classic Walls retains wall death and finished state',()=>{
  const g=fresh();g.snake.positions=[[39,10]];const s=E.settings(cfg,{wrapWalls:false});
  E.step(g,s);assert.equal(g.cause,'wall');const snapshot=E.snapshot(g);E.step(g,s);assert.deepEqual(E.snapshot(g),snapshot);
});
test('invalid food plan/rng never creates out-of-bounds food',()=>{
  assert.deepEqual(E.placeItem([],cfg,[[-1,2],[40,0],[2.5,1],null,[3,4]],null),[3,4]);
  assert.deepEqual(E.placeItem([],cfg,[],()=>2),[0,0]);
});
test('invalid turns cannot corrupt heading',()=>{
  const g=fresh();for(const d of [null,[0,0],[1,1],[2,0],[.5,.5]])assert.equal(E.turn(g,d),false);
  assert.deepEqual(g.snake.direction,[1,0]);
});
test('Right → Up → Left applies one turn per real tick',()=>{
  const g=fresh(),q=C.createQueue();g.snake.length=3;
  assert.equal(q.offer([0,-1],g.snake.direction,1),'accepted');
  assert.equal(q.offer([-1,0],g.snake.direction,2),'accepted');
  assert.deepEqual(g.snake.direction,[1,0]);
  for(const expected of [[20,14],[19,14]]){const c=q.take(20);assert.ok(E.turn(g,c.dir));E.step(g,E.settings(cfg));assert.deepEqual(g.snake.positions[0],expected);}
  assert.equal(q.size(),0);
});
test('projected reversal and duplicate are rejected, overflow keeps first two',()=>{
  const q=C.createQueue();const r=[1,0];
  assert.equal(q.offer(r,r,0),'duplicate');assert.equal(q.offer([-1,0],r,0),'reverse');
  assert.equal(q.offer([0,-1],r,1),'accepted');assert.equal(q.offer([0,1],r,2),'reverse');
  assert.equal(q.offer([0,-1],r,2),'duplicate');assert.equal(q.offer([-1,0],r,3),'accepted');
  assert.equal(q.offer([0,1],r,4),'full');assert.equal(q.size(),2);
  assert.deepEqual(q.take(5).dir,[0,-1]);assert.deepEqual(q.take(6).dir,[-1,0]);
});
test('stale projected chain expires together; clear discards inputs',()=>{
  const q=C.createQueue();q.offer([0,-1],[1,0],0);q.offer([-1,0],[1,0],1);
  assert.equal(q.take(501),null);assert.equal(q.offer([-1,0],[1,0],502),'reverse');
  q.offer([0,1],[1,0],503);q.clear();assert.equal(q.take(504),null);
});
test('swipe recognizes on move, jitter/diagonal/multi-pointer and release are inert',()=>{
  const out=[],sw=C.createSwipe(d=>{out.push(d);return true;});
  assert.ok(sw.start(1,50,50));assert.equal(sw.start(2,0,0),false);
  assert.equal(sw.move(2,50,90),false);assert.equal(sw.move(1,51,49),false);
  assert.equal(sw.move(1,64,64),false);assert.ok(sw.move(1,50,34));
  assert.deepEqual(out,[[0,-1]]);assert.ok(sw.move(1,34,34));
  sw.end(1);assert.equal(sw.move(1,34,70),false);assert.deepEqual(out,[[0,-1],[-1,0]]);
});
test('swipe cancellation and capture loss never emit, rejected segment keeps origin',()=>{
  let accepts=false,calls=0;const sw=C.createSwipe(()=>{calls++;return accepts;});
  sw.start(1,10,10);assert.equal(sw.move(1,30,10),false);accepts=true;
  assert.ok(sw.move(1,30,10));sw.end(2);assert.ok(sw.move(1,30,30));
  sw.clear();assert.equal(sw.move(1,30,60),false);assert.equal(calls,3);
});
for(const rate of cfg.speedLevels) for(const fps of [30,60,144])
test(rate+' ticks/s independent of '+fps+' render FPS',()=>{
  const clock=C.createClock(rate);clock.reset(0);let ticks=0;
  for(let i=1;i<=fps*10;i++)clock.advance(i*1000/fps,()=>{ticks++;});
  assert.equal(ticks,rate*10);assert.equal(clock.period(),1000/rate);
});
test('live speed rebases to one full new period with no catch-up or state reset',()=>{
  const c=C.createClock(5);c.reset(0);let ticks=0;
  c.advance(190,()=>ticks++);c.setRate(20,190);
  c.advance(239,()=>ticks++);assert.equal(ticks,0);
  c.advance(240,()=>ticks++);assert.equal(ticks,1);
  c.setRate(12,240);c.advance(240+1000/12,()=>ticks++);assert.equal(ticks,2);
});
test('stalls are bounded at three steps, resume has no hidden catch-up',()=>{
  const c=C.createClock(20);c.reset(0);let ticks=0;
  const result=c.advance(5000,()=>ticks++);assert.equal(ticks,3);assert.ok(result.droppedMs>=4800);
  c.reset();c.advance(50000,()=>ticks++);assert.equal(ticks,3);
  c.advance(50050,()=>false);assert.equal(ticks,3);
});
test('no queue consumption on a frame without a simulation tick',()=>{
  const q=C.createQueue(),c=C.createClock(5);c.reset(0);q.offer([0,-1],[1,0],0);
  c.advance(100,()=>q.take(100));assert.equal(q.size(),1);
  c.advance(200,()=>q.take(200));assert.equal(q.size(),0);
});
