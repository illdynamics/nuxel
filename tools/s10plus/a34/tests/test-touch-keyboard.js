// Exercise editing/selection/events against the shipped keyboard, no input injection.
const fs = require('fs'), vm = require('vm'), path = require('path'), assert = require('assert');
const win = {navigator:{userAgent:'Nuxel/1.0 (S10+, like Gecko)'}};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../../../../pwa/nuxel-home/js/touch-keyboard.js'), 'utf8'), {window:win});
class Event { constructor(type, args) { this.type = type; Object.assign(this, args); } }
function field(value = '') {
    return {tagName:'INPUT', type:'search', isConnected:true, disabled:false, readOnly:false,
        focus() {}, value, selectionStart:value.length, selectionEnd:value.length, maxLength:-1,
        ownerDocument:{defaultView:{InputEvent:Event, KeyboardEvent:Event}}, events:[],
        dispatchEvent(e) { this.events.push(e); return !this.cancelBefore || e.type !== 'beforeinput'; },
        setRangeText(s,a,b) { this.value = this.value.slice(0,a) + s + this.value.slice(b); this.selectionStart = this.selectionEnd = a+s.length; }};
}
const edit = win.NuxelTouchKeyboard.edit;
let el = field();
for (const c of 'NUXEL') assert(edit(el,c));
assert.equal(el.value,'NUXEL');
assert.equal(el.events.filter(e=>e.type==='input').length,5);
console.log('PASS touchscreen keyboard enters NUXEL and emits one input per key');
el.selectionStart=0; el.selectionEnd=5; edit(el,'Phone'); assert.equal(el.value,'Phone');
edit(el,'Backspace'); assert.equal(el.value,'Phon');
console.log('PASS selection replacement and backspace preserve cursor');
el=field('A🐧'); edit(el,'Backspace'); assert.equal(el.value,'A');
el.maxLength=1; assert(!edit(el,'B')); assert.equal(el.value,'A');
el.maxLength=-1; el.cancelBefore=true; assert(!edit(el,'B')); assert.equal(el.value,'A');
el.readOnly=true; assert(!edit(el,'B')); assert.equal(el.value,'A');
console.log('PASS Unicode deletion, maxlength, beforeinput cancellation and readonly');
el=field(); edit(el,'Enter'); assert.deepEqual(el.events.map(e=>e.type),['keydown','keyup']);
el=field(); el.tagName='TEXTAREA'; edit(el,'Enter'); assert.equal(el.value,'\n');
console.log('PASS Search Enter and multiline newline keep their distinct behavior');
