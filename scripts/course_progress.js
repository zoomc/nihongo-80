(function () {
  'use strict';
  const key = 'nh80.course.v18';
  const valid = day => Number.isInteger(day) && day >= 1 && day <= 150;
  const read = name => { try { return localStorage.getItem(name); } catch { return null; } };
  function parse(code) {
    const match = /^NH18-(\d{1,3})-([0-9a-f]{38})$/i.exec(code || '');
    if (!match || (!valid(Number(match[1])) && match[1] !== '0') || parseInt(match[2][37], 16) > 3) return null;
    const done = new Set();
    for (let day = 1; day <= 150; day++) {
      const bit = day - 1;
      if (parseInt(match[2][bit >> 2], 16) & (1 << (bit % 4))) done.add(day);
    }
    return {last: Number(match[1]), done};
  }
  function encode({last, done}) {
    const bits = new Array(38).fill(0);
    for (const day of done) bits[(day - 1) >> 2] |= 1 << ((day - 1) % 4);
    return 'NH18-' + last + '-' + bits.map(n => n.toString(16)).join('');
  }
  const local = parse(read(key));
  const cookie = parse(document.cookie.match(/(?:^|;\s*)nh80_course=([^;]+)/)?.[1]);
  const state = {last: local?.last || cookie?.last || 0, done: new Set([...(local?.done || []), ...(cookie?.done || [])])};
  const old = Number(read('nh80.v16.lastDay') || read('nh80.v15.lastDay') || read('nh80.v11.lastDay') || 0);
  for (let day = 1; day <= 150; day++) {
    if ((valid(old) && day <= old) || read('nh80.completed.' + day) === '1') state.done.add(day);
  }
  let opened = Number(read('nh80.course.opened')) || (state.last ? 1 : 0);
  function save() {
    const code = encode(state);
    try { localStorage.setItem(key, code); localStorage.setItem('nh80.course.opened', opened); } catch {}
    if (location.protocol === 'https:') document.cookie = 'nh80_course=' + code + '; Max-Age=31536000; Path=/; SameSite=Strict; Secure';
  }
  if (state.last || state.done.size) save();
  window.NHCourse = {
    last: () => state.last,
    done: day => state.done.has(day),
    next() {
      for (let day = 1; day <= 150; day++) if (!state.done.has(day)) return day;
      return 0;
    },
    open(day) {
      if (valid(day) && (state.last !== day || !opened)) {
        state.last = day; opened = Date.now(); save();
        window.dispatchEvent(new Event('nh80-course-change'));
      }
    },
    finish(day) { if (valid(day)) { state.done.add(day); save(); window.dispatchEvent(new Event('nh80-course-change')); } },
    code: () => encode(state),
    snapshot: () => ({days:[...state.done], last:state.last, opened}),
    applyCloud(remote) {
      const before = encode(state);
      for (const day of remote.days) state.done.add(day);
      if (remote.opened > opened) { state.last = remote.last; opened = remote.opened; }
      save();
      if (before !== encode(state)) window.dispatchEvent(new Event('nh80-cloud-change'));
    },
    merge(code) {
      const imported = parse(code.trim());
      if (!imported) return false;
      for (const day of imported.done) state.done.add(day);
      if (imported.last && (!state.last || state.done.has(state.last))) {
        state.last = imported.last;
        opened = Date.now();
      }
      save();
      window.dispatchEvent(new Event('nh80-course-change'));
      return true;
    }
  };
})();
