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

  // Only one checkbox per White column
  document.querySelectorAll('#ai-model-list input[id^="white-"]').forEach(function(checkbox) {
    checkbox.addEventListener('change', function () {
      if (this.checked) {
        document.querySelectorAll('#ai-model-list input[id^="white-"]').forEach(function(box) {
          if (box !== checkbox) box.checked = false;
        });
      }
      if (this.id === 'white-hu') {
        document.getElementById('black-hu').disabled = this.checked;
        console.debug('player-selection.js: white-hu changed, checked:', this.checked);
      } else {
        // If a non-human is selected for White, enable Black human checkbox
        document.getElementById('black-hu').disabled = false;
        console.debug('player-selection.js: non-human white selected, black-hu enabled');
      }
    });
  });

  // Only one checkbox per Black column
  document.querySelectorAll('#ai-model-list input[id^="black-"]').forEach(function(checkbox) {
    checkbox.addEventListener('change', function () {
      if (this.checked) {
        document.querySelectorAll('#ai-model-list input[id^="black-"]').forEach(function(box) {
          if (box !== checkbox) box.checked = false;
        });
      }
      if (this.id === 'black-hu') {
        document.getElementById('white-hu').disabled = this.checked;
        console.debug('player-selection.js: black-hu changed, checked:', this.checked);
      } else {
        // If a non-human is selected for Black, enable White human checkbox
        document.getElementById('white-hu').disabled = false;
        console.debug('player-selection.js: non-human black selected, white-hu enabled');
      }
    });
  });

  // Reset button logic: uncheck and re-enable all checkboxes
  document.getElementById('resetPlayersBtn').addEventListener('click', function () {
    const checkboxes = document.querySelectorAll('#ai-model-list input[type="checkbox"]');
    checkboxes.forEach(function(box) {
      box.checked = false;
      box.disabled = false;
    });
    // Reset player-info display
    document.getElementById('player-info-white').textContent = '';
    document.getElementById('player-info-black').textContent = '';
    console.debug('player-selection.js: resetPlayersBtn clicked, all checkboxes reset');
  });

  // Set button logic: set player names in player-info box
  document.getElementById('setPlayersBtn').addEventListener('click', function () {
    // Find checked white and black player
    const white = document.querySelector('#ai-model-list input[id^="white-"]:checked');
    const black = document.querySelector('#ai-model-list input[id^="black-"]:checked');
    // Map checkbox id to display name
    function getPlayerName(id) {
      if (!id) return '';
      if (id === 'hu') return 'Human';
      if (id === 'm1') return 'openai/gpt-4o';
      if (id === 'm2') return 'deepseek/deepseek-chat-v3.1';
      if (id === 'm3') return 'google/gemini-2.5-pro';
      if (id === 'm4') return 'anthropic/claude-3-opus';
      if (id === 'm5') return 'meta-llama/llama-3-70b-instruct';
      if (id === 's1') return 'Skill level: 5';
      if (id === 's2') return 'Skill level: 10';
      if (id === 's3') return 'Skill level: 20';
      return id;
    }
    let whitePlayer = white ? getPlayerName(white.id.replace('white-', '')) : '';
    let blackPlayer = black ? getPlayerName(black.id.replace('black-', '')) : '';
    document.getElementById('player-info-white').textContent = whitePlayer;
    document.getElementById('player-info-black').textContent = blackPlayer;
  });
});