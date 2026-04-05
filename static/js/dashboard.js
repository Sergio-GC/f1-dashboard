async function loadData() {
    try {
        // Get the json data from the api
        var res = await fetch('/api/data');
        var data = await res.json();

        // Display the data
        render(data);

        // Change the Updated time on top right
        document.getElementById('status').textContent =
            'Updated: ' + new Date().toLocaleTimeString();
    } catch (e) {
        document.getElementById('app').innerHTML =
            '<div class="card"><p class="error">Failed to load data</p></div>';
    }
}

function render(data) {
    var app = document.getElementById('app');
    app.innerHTML = '';

    // Next Race card
    app.appendChild(renderNextRace(data.next_race));
}

function renderNextRace(race) {
    var card = document.createElement('div');
    card.className = 'card wide';

    // If there is no next race, inform the user
    if (!race) {
        card.innerHTML = '<h2>Next Race</h2><p>No upcoming race found</p>';
        return card;
    }

    // Display the card with the next race's data
    card.innerHTML =
        '<h2>Round ' + race.round + ' — ' + race.name + '</h2>' +
        '<div class="race-name">' + race.name + '</div>' + '<br>' +
        '<div class="race-detail">📍 ' + race.circuit_name + '</div>' +
        '<div class="race-detail">🌎 ' + race.locality + ', ' + race.country + '</div>' +
        '<div class="race-detail">📅 ' + race.date + ' — ' + race.time + '</div>';

    return card;
}

// Load once on startup
loadData();