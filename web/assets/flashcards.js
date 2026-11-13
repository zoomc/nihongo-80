(function () {
  'use strict';
  let words;
  let round;

  function shuffled(items) {
    const copy = items.slice();
    for (let i = copy.length - 1; i > 0; i--) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  window.mountFlashcards = async function (root, signal) {
    if (!root) return;
    const find = selector => root.querySelector(selector);
    const status = find('#flashStatus');
    const deck = find('#flashDeck');
    const flip = find('#flashFlip');
    const actions = find('#flashActions');
    const answer = find('#flashAnswer');
    const again = find('#flashAgain');
    const say = find('#flashSpeak');
    const restart = find('#flashRestart');
    const retry = find('#flashRetry');
    const empty = find('#flashEmpty');
    let pool = [];

    function render(focus = false) {
      const card = round.cards[round.index];
      deck.hidden = !card;
      restart.hidden = !!card;
      if (!card) {
        status.textContent = '本轮完成 · 回忆了 ' + round.total + ' 个词';
        if (focus) restart.focus();
        return;
      }
      status.textContent = (round.retry ? '重练' : '本轮') + ' ' + (round.index + 1) + ' / ' + round.cards.length;
      find('#flashWord').textContent = card.front;
      find('#flashKana').textContent = card.kana;
      find('#flashMeaning').textContent = card.back;
      find('#flashKo').textContent = card.ko || '';
      say.dataset.speak = (card.kana || card.front).split('／')[0];
      answer.hidden = actions.hidden = !round.revealed;
      flip.hidden = round.revealed;
      again.textContent = round.retry ? '还不熟' : '忘了';
      if (focus) (round.revealed ? again : flip).focus();
    }

    function start() {
      const cards = shuffled(pool).slice(0, 20);
      round = {cards, total: cards.length, index: 0, missed: [], retry: false, revealed: false};
    }

    function grade(forgot) {
      if (!round.revealed) return;
      if (forgot && !round.retry) round.missed.push(round.cards[round.index]);
      round.index++;
      round.revealed = false;
      if (round.index === round.cards.length && round.missed.length) {
        round.cards = shuffled(round.missed);
        round.missed = [];
        round.retry = true;
        round.index = 0;
      }
      render(true);
    }

    async function load() {
      retry.hidden = true;
      status.textContent = '正在加载词卡…';
      try {
        if (!words) {
          const response = await fetch('/data/flashcards.json', {signal});
          if (!response.ok) throw Error('词库不可用');
          words = await response.json();
        }
      } catch {
        if (!signal.aborted) {
          status.textContent = '词库暂时无法打开。';
          retry.hidden = false;
        }
        return;
      }
      if (signal.aborted) return;
      pool = words.filter(card => NHCourse.done(card.day));
      if (!pool.length) {
        status.textContent = '完成一节日课后，就能在这里背当天的词。';
        empty.hidden = false;
        return;
      }
      if (!round || !round.cards.every(card => NHCourse.done(card.day))) start();
      render();
    }

    flip.onclick = () => { round.revealed = true; render(true); };
    again.onclick = () => grade(true);
    find('#flashKnow').onclick = () => grade(false);
    restart.onclick = () => { start(); render(true); };
    retry.onclick = load;
    say.hidden = !window.speechSynthesis;
    await load();
  };
})();
