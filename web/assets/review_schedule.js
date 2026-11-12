/* Browser recall practice. SQLite/FSRS remains the authority for session reviews. */
(function () {
  'use strict';

  const KEY = 'nh80.review.v1';
  const LESSON = 'nh80.v11.state.';
  const INTERVALS = [1, 3, 7, 14, 30, 60];
  const QUESTION = /^D(?:13|15)-(\d{3})-([VG]\d{4})-[a-z]+$/;

  function today(date = new Date()) {
    return Math.floor(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate()) / 86400000);
  }

  function read(key) {
    try {
      return JSON.parse(localStorage.getItem(key)) || {};
    } catch {
      return {};
    }
  }

  function parseAnswer(qid, day) {
    const match = QUESTION.exec(qid);
    return match && Number(match[1]) === day ? match[2] : null;
  }

  function addLesson(cards, day, results, date, historical) {
    const outcomes = new Map();
    for (const [qid, answer] of Object.entries(results || {})) {
      const kid = parseAnswer(qid, day);
      if (kid && typeof answer?.correct === 'boolean') {
        outcomes.set(kid, outcomes.get(kid) !== false && answer.correct);
      }
    }
    let changed = false;
    for (const [kid, correct] of outcomes) {
      const card = cards[kid];
      if (!card) {
        cards[kid] = { due: date + (correct && !historical ? 1 : 0), step: -1, missed: !correct };
        changed = true;
      } else if (card.reviewed === undefined && !correct && !card.missed) {
        card.missed = true;
        card.due = Math.min(card.due, date);
        changed = true;
      }
    }
    return changed;
  }

  function lesson(day, results) {
    const cards = read(KEY);
    if (addLesson(cards, day, results, today(), false)) {
      localStorage.setItem(KEY, JSON.stringify(cards));
    }
  }

  function recover() {
    const cards = read(KEY);
    if (cards._history) return;
    const date = today();
    for (let day = 1; day <= 120; day++) {
      addLesson(cards, day, read(LESSON + day).results, date, true);
    }
    cards._history = true;
    localStorage.setItem(KEY, JSON.stringify(cards));
  }

  function due(date = today()) {
    return Object.entries(read(KEY))
      .filter(([, card]) => card && Number.isInteger(card.due) && card.due <= date)
      .map(([kid, card]) => ({ kid, ...card }))
      .sort((a, b) => a.due - b.due || Number(b.missed) - Number(a.missed) || a.kid.localeCompare(b.kid));
  }

  function rate(kid, rating, date = today()) {
    const cards = read(KEY);
    const card = cards[kid];
    if (!card || card.due > date || !['again', 'hard', 'good'].includes(rating)) return null;
    let step = card.step;
    let interval = 1;
    if (rating === 'again') step = -1;
    if (rating === 'hard') interval = Math.max(1, Math.floor((INTERVALS[step] || 1) / 2));
    if (rating === 'good') {
      step = Math.min(step + 1, INTERVALS.length - 1);
      interval = INTERVALS[step];
    }
    cards[kid] = { due: date + interval, step, missed: rating === 'again', reviewed: date, rating };
    localStorage.setItem(KEY, JSON.stringify(cards));
    return interval;
  }

  function ratings() {
    return Object.fromEntries(Object.entries(read(KEY))
      .filter(([, card]) => card?.rating)
      .map(([kid, card]) => [kid, card.rating]));
  }

  function wrongQuestions() {
    const questions = [];
    for (let day = 120; day >= 1; day--) {
      const { results, retry } = read(LESSON + day);
      for (const [qid, result] of Object.entries(results || {})) {
        const kid = parseAnswer(qid, day);
        if (kid && result?.correct === false) {
          questions.push({ qid, day, knowledge_ids: [kid], wrong_count: 1,
            last_correct: Number(retry?.results?.[qid]?.correct === true) });
        }
      }
    }
    return questions;
  }

  window.NHReview = { lesson, recover, due, rate, ratings, wrongQuestions };
})();
