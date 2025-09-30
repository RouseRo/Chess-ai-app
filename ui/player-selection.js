document.addEventListener('DOMContentLoaded', function () {
  // Debug: Log when DOM is loaded
  console.debug('player-selection.js: DOMContentLoaded');

  // Show Players tab panel logic
  function showPlayersTabPanel() {
    console.debug('player-selection.js: showPlayersTabPanel called');
    document.querySelectorAll('.tab-content').forEach(el => el.style.display = 'none');
    document.getElementById('players-tab').style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    document.querySelector('.tab-btn:nth-child(2)').classList.add('active');
  }

  // Human player selection logic
  document.getElementById('white-hu').addEventListener('change', function () {
    document.getElementById('black-hu').disabled = this.checked;
    console.debug('player-selection.js: white-hu changed, checked:', this.checked);
  });

  document.getElementById('black-hu').addEventListener('change', function () {
    document.getElementById('white-hu').disabled = this.checked;
    console.debug('player-selection.js: black-hu changed, checked:', this.checked);
  });

  // Reset button logic: uncheck and re-enable all checkboxes
  document.getElementById('resetPlayersBtn').addEventListener('click', function () {
    const checkboxes = document.querySelectorAll('#ai-model-list input[type="checkbox"]');
    checkboxes.forEach(function(box) {
      box.checked = false;
      box.disabled = false;
    });
    console.debug('player-selection.js: resetPlayersBtn clicked, all checkboxes reset');
  });

  // Set button logic: collect selected players for White and Black
  document.getElementById('setPlayersBtn').addEventListener('click', function () {
    const white = document.querySelector('#ai-model-list input[id^="white-"]:checked');
    const black = document.querySelector('#ai-model-list input[id^="black-"]:checked');
    let whitePlayer = white ? white.id.replace('white-', '') : null;
    let blackPlayer = black ? black.id.replace('black-', '') : null;
    console.debug('player-selection.js: setPlayersBtn clicked');
    console.debug('Selected White:', whitePlayer);
    console.debug('Selected Black:', blackPlayer);
  });
});