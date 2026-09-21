// Pure draw logic for the sample-question shuffle (no DOM, so it can be
// unit-tested under node). Stratified: pick DRAW_SIZE distinct categories at
// random, then one question from each, so every draw shows real variety
// (never more than one question per category while >= DRAW_SIZE categories
// exist, which is always true for the shipped pool).
(function (root) {
  "use strict";
  var DRAW_SIZE = 4;

  function shuffled(arr, rng) {
    var a = arr.slice();
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rng() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }

  // pool: [{id, category, label, question}]; previousIds: ids shown last time
  // (avoided when possible so a shuffle visibly changes the set).
  function drawSamples(pool, previousIds, rng) {
    rng = rng || Math.random;
    var prev = {};
    (previousIds || []).forEach(function (id) { prev[id] = true; });

    var fresh = pool.filter(function (q) { return !prev[q.id]; });
    var byCat = {};
    fresh.forEach(function (q) { (byCat[q.category] = byCat[q.category] || []).push(q); });
    // categories whose only questions were all just shown fall back to the full pool
    pool.forEach(function (q) { byCat[q.category] = byCat[q.category] || pool.filter(function (p) { return p.category === q.category; }); });

    var cats = shuffled(Object.keys(byCat), rng).slice(0, DRAW_SIZE);
    return cats.map(function (c) {
      var options = byCat[c];
      return options[Math.floor(rng() * options.length)];
    });
  }

  var api = { drawSamples: drawSamples, DRAW_SIZE: DRAW_SIZE };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.AeroOpsSamples = api;
})(typeof window !== "undefined" ? window : globalThis);
