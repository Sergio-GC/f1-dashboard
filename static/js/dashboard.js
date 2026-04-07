var countdownTimer = null;

async function loadData() {
  try {
    var res = await fetch('/api/data');
    var data = await res.json();
    render(data);
    document.getElementById('status').textContent =
      'Updated: ' + new Date().toLocaleTimeString();
  } catch (e) {
    document.getElementById('app').innerHTML =
      '<div class="alert alert-danger">Failed to load data. Retrying in 60s...</div>';
  }
}

function render(data) {
  var app = document.getElementById('app');
  app.innerHTML = '';
  if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }

  var row1 = document.createElement('div');
  row1.className = 'row g-3 mb-3';
  row1.innerHTML =
    '<div class="col-lg-7">' + renderNextRace(data.next_race, data.lap_record, data.weather) + '</div>' +
    '<div class="col-lg-5">' + renderLastRaceResults(data.last_race_results) + '</div>';
  app.appendChild(row1);

  var row2 = document.createElement('div');
  row2.className = 'row g-3 mb-3';
  row2.innerHTML =
    '<div class="col-lg-7">' + renderDriverStandings(data.driver_standings) + '</div>' +
    '<div class="col-lg-5">' + renderConstructorStandings(data.constructor_standings) + '</div>';
  app.appendChild(row2);

  var row3 = document.createElement('div');
  row3.className = 'row g-3 mb-3';
  row3.innerHTML = '<div class="col-12">' + renderNews(data.news) + '</div>';
  app.appendChild(row3);

  // Start countdown after DOM is ready
  if (data.next_race) {
    var session = findNextImportantSession(data.next_race.sessions);
    if (session) startCountdown(session);
  }
}

/* ── Next Race ── */

function renderNextRace(race, lapRecord, weather) {
  if (!race) return cardWrap('Next Race', '<p class="text-secondary">No upcoming race</p>');

  var sprintBadge = race.is_sprint
    ? ' <span class="badge bg-warning text-dark sprint-badge">Sprint Weekend</span>'
    : '';

  var sessions = '';
  var labels = {sprint_qualifying:'Sprint Quali', sprint:'Sprint', qualifying:'Qualifying', race:'Race'};
  for (var key in labels) {
    if (race.sessions[key]) {
      var rowCls = key === 'race' ? 'session-row-race' : '';
      sessions +=
        '<div class="d-flex justify-content-between align-items-center p-2 rounded mb-1 bg-dark ' + rowCls + '">' +
        '<span class="text-uppercase small text-secondary session-label">' + labels[key] + '</span>' +
        '<span class="small fw-semibold session-time">' + race.sessions[key].display + '</span></div>';
    }
  }

  var nextSession = findNextImportantSession(race.sessions);
  var countdownHtml = '';
  if (nextSession) {
    countdownHtml =
      '<div class="bg-dark border border-danger border-opacity-50 rounded p-3 text-center mb-3">' +
      '<div class="text-uppercase small text-secondary mb-1">⏱ Countdown to ' + nextSession.label + '</div>' +
      '<div class="countdown-time" id="countdown-time">--</div>' +
      '<div class="small text-secondary mt-1">' + nextSession.display + '</div></div>';
  }

  var infoCards = '';
  if (lapRecord) {
    infoCards +=
      '<div class="col"><div class="bg-dark rounded p-2">' +
      '<div class="text-uppercase small text-secondary" style="font-size:0.65rem">Lap Record</div>' +
      '<div class="fw-bold">' + lapRecord.time + '</div>' +
      '<div class="small text-secondary">' + lapRecord.driver + ' (' + lapRecord.year + ')</div></div></div>';
  }
  if (weather) {
    infoCards +=
      '<div class="col"><div class="bg-dark rounded p-2">' +
      '<div class="text-uppercase small text-secondary" style="font-size:0.65rem">Race Day Weather</div>' +
      '<div class="fw-bold">' + weather.condition + '</div>' +
      '<div class="small text-secondary">' +
      weather.temp_min + '°C – ' + weather.temp_max + '°C · Rain: ' + weather.rain_chance + '%</div></div></div>';
  }
  var infoGrid = infoCards ? '<div class="row g-2 mt-2">' + infoCards + '</div>' : '';

  return cardWrap('Round ' + race.round + ' — Next Race',
    '<h5 class="fw-bold mb-1">' + race.name + sprintBadge + '</h5>' +
    '<p class="text-secondary small mb-3">📍 ' + race.circuit_name + ', ' + race.locality + ', ' + race.country + '</p>' +
    countdownHtml + sessions + infoGrid
  );
}

/* ── Last Race Results ── */

function renderLastRaceResults(lr) {
  if (!lr) return cardWrap('Last Race Results', '<p class="text-secondary">No data</p>');

  var rows = '';
  lr.results.forEach(function(r) {
    var posClass = parseInt(r.pos) <= 3 ? 'text-warning fw-bold' : '';
    var flIcon = r.fastest_lap ? ' <span class="fl-icon">⚡FL</span>' : '';
    var delta = gridDelta(r.grid, r.pos);
    var pts = r.points > 0 ? r.points : '';
    rows +=
      '<tr>' +
      '<td class="' + posClass + '">' + r.pos + '</td>' +
      '<td>' + r.name + flIcon + '</td>' +
      '<td class="text-secondary small">' + r.team + '</td>' +
      '<td>' + delta + '</td>' +
      '<td class="text-end text-danger fw-semibold">' + pts + '</td></tr>';
  });

  return cardWrap('Last Race — ' + lr.race_name,
    '<table class="table table-dark table-sm table-hover mb-0">' +
    '<thead><tr><th>#</th><th>Driver</th><th>Team</th><th>+/-</th><th class="text-end">Pts</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>'
  );
}

/* ── Driver Standings ── */

function renderDriverStandings(standings) {
  if (!standings || !standings.length) return cardWrap('Drivers Championship', '<p class="text-secondary">No data</p>');

  var rows = '';
  var prevPoints = null;
  standings.forEach(function(s, i) {
    var posClass = parseInt(s.pos) <= 3 ? 'text-warning fw-bold' : '';
    var gap = '';
    if (i > 0 && prevPoints !== null) {
      var diff = parseFloat(prevPoints) - parseFloat(s.points);
      gap = '<span class="text-secondary">-' + diff + '</span>';
    }
    prevPoints = s.points;
    rows +=
      '<tr>' +
      '<td class="' + posClass + '">' + s.pos + '</td>' +
      '<td class="fw-semibold">' + s.code + ' <span class="text-secondary fw-normal">' + s.name + '</span></td>' +
      '<td class="text-secondary small">' + s.team + '</td>' +
      '<td class="text-center">' + s.wins + '</td>' +
      '<td class="text-end text-danger fw-bold">' + s.points + '</td>' +
      '<td class="text-end small">' + gap + '</td></tr>';
  });

  return cardWrap('Drivers Championship',
    '<table class="table table-dark table-sm table-hover mb-0">' +
    '<thead><tr><th>#</th><th>Driver</th><th>Team</th><th class="text-center">W</th><th class="text-end">Pts</th><th class="text-end">Gap</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>'
  );
}

/* ── Constructor Standings ── */

function renderConstructorStandings(standings) {
  if (!standings || !standings.length) return cardWrap('Constructors Championship', '<p class="text-secondary">No data</p>');

  var rows = '';
  var prevPoints = null;
  standings.forEach(function(s, i) {
    var posClass = parseInt(s.pos) <= 3 ? 'text-warning fw-bold' : '';
    var gap = '';
    if (i > 0 && prevPoints !== null) {
      var diff = parseFloat(prevPoints) - parseFloat(s.points);
      gap = '<span class="text-secondary">-' + diff + '</span>';
    }
    prevPoints = s.points;
    rows +=
      '<tr>' +
      '<td class="' + posClass + '">' + s.pos + '</td>' +
      '<td class="fw-semibold">' + s.name + '</td>' +
      '<td class="text-center">' + s.wins + '</td>' +
      '<td class="text-end text-danger fw-bold">' + s.points + '</td>' +
      '<td class="text-end small">' + gap + '</td></tr>';
  });

  return cardWrap('Constructors Championship',
    '<table class="table table-dark table-sm table-hover mb-0">' +
    '<thead><tr><th>#</th><th>Team</th><th class="text-center">W</th><th class="text-end">Pts</th><th class="text-end">Gap</th></tr></thead>' +
    '<tbody>' + rows + '</tbody></table>'
  );
}

/* ── News ── */

function renderNews(articles) {
  if (!articles || !articles.length) return cardWrap('Latest F1 News', '<p class="text-secondary">No news</p>');

  var items = '';
  articles.slice(0, 20).forEach(function(a) {
    items +=
      '<div class="news-item p-2 rounded mb-2 bg-dark">' +
      '<a href="' + a.link + '" target="_blank" rel="noopener" class="text-decoration-none text-light fw-semibold small">' + a.title + '</a>' +
      '<div class="d-flex gap-2 mt-1" style="font-size:0.7rem">' +
      '<span class="text-success fw-semibold">' + a.source + '</span>' +
      '<span class="text-secondary">' + a.date + '</span></div>' +
      (a.summary ? '<div class="text-secondary mt-1" style="font-size:0.75rem">' + a.summary + '</div>' : '') +
      '</div>';
  });

  return cardWrap('Latest F1 News', items);
}

/* ── Helpers ── */

function cardWrap(title, content) {
  return '<div class="card bg-dark border-secondary">' +
    '<div class="card-header border-danger border-top border-3 bg-transparent">' +
    '<h6 class="text-uppercase text-secondary small fw-semibold mb-0">' + title + '</h6></div>' +
    '<div class="card-body">' + content + '</div></div>';
}

function gridDelta(grid, pos) {
  var g = parseInt(grid), p = parseInt(pos);
  if (isNaN(g) || isNaN(p) || g === 0) return '<span class="delta-neutral">—</span>';
  var diff = g - p;
  if (diff > 0) return '<span class="delta-gained">▲' + diff + '</span>';
  if (diff < 0) return '<span class="delta-lost">▼' + Math.abs(diff) + '</span>';
  return '<span class="delta-neutral">=</span>';
}

function findNextImportantSession(sessions) {
  var now = new Date();
  var best = null;
  ['qualifying', 'race'].forEach(function(key) {
    if (!sessions[key]) return;
    var dt = new Date(sessions[key].utc);
    if (dt > now && (!best || dt < best.dt)) {
      best = { key: key, label: key === 'qualifying' ? 'Qualifying' : 'Race', dt: dt, display: sessions[key].display };
    }
  });
  return best;
}

function startCountdown(session) {
  var el = document.getElementById('countdown-time');
  if (!el) return;
  function tick() {
    var diff = session.dt - new Date();
    if (diff <= 0) { el.textContent = 'NOW!'; clearInterval(countdownTimer); return; }
    var d = Math.floor(diff / 86400000);
    var h = Math.floor((diff % 86400000) / 3600000);
    var m = Math.floor((diff % 3600000) / 60000);
    var s = Math.floor((diff % 60000) / 1000);
    var parts = [];
    if (d > 0) parts.push(d + 'd');
    parts.push(h + 'h ' + m + 'm ' + s + 's');
    el.textContent = parts.join(' ');
  }
  tick();
  countdownTimer = setInterval(tick, 1000);
}

loadData();
setInterval(loadData, 60000);
