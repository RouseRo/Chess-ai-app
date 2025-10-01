document.addEventListener('DOMContentLoaded', function () {
  // Debug: Log when DOM is loaded
  console.debug('player-selection.ts: DOMContentLoaded');

  // Show Players tab panel logic
  function showPlayersTabPanel() {
    console.debug('player-selection.ts: showPlayersTabPanel called');
    document.querySelectorAll('.tab-content').forEach(el => {
      (el as HTMLElement).style.display = 'none';
    });
    const playersTab = document.getElementById('players-tab');
    if (playersTab) playersTab.style.display = 'block';
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
    const tabBtn = document.querySelector('.tab-btn:nth-child(2)');
    if (tabBtn) tabBtn.classList.add('active');
  }

  // Only one checkbox per White column
  document.querySelectorAll<HTMLInputElement>('#ai-model-list input[id^="white-"]').forEach(function(checkbox) {
    checkbox.addEventListener('change', function () {
      if (checkbox.checked) {
        document.querySelectorAll<HTMLInputElement>('#ai-model-list input[id^="white-"]').forEach(function(box) {
          if (box !== checkbox) box.checked = false;
        });
      }
      if (checkbox.id === 'white-hu') {
        const blackHu = document.getElementById('black-hu') as HTMLInputElement | null;
        if (blackHu) blackHu.disabled = checkbox.checked;
        document.querySelectorAll<HTMLInputElement>('#white-openings-list input[type="checkbox"]').forEach(box => {
          box.disabled = checkbox.checked;
          if (checkbox.checked) box.checked = false;
        });
      } else {
        const blackHu = document.getElementById('black-hu') as HTMLInputElement | null;
        if (blackHu) blackHu.disabled = false;
        document.querySelectorAll<HTMLInputElement>('#white-openings-list input[type="checkbox"]').forEach(box => {
          box.disabled = false;
        });
      }
    });
  });

  // Only one checkbox per Black column
  document.querySelectorAll<HTMLInputElement>('#ai-model-list input[id^="black-"]').forEach(function(checkbox) {
    checkbox.addEventListener('change', function () {
      if (checkbox.checked) {
        document.querySelectorAll<HTMLInputElement>('#ai-model-list input[id^="black-"]').forEach(function(box) {
          if (box !== checkbox) box.checked = false;
        });
      }
      if (checkbox.id === 'black-hu') {
        const whiteHu = document.getElementById('white-hu') as HTMLInputElement | null;
        if (whiteHu) whiteHu.disabled = checkbox.checked;
        document.querySelectorAll<HTMLInputElement>('#black-defenses-list input[type="checkbox"]').forEach(box => {
          box.disabled = checkbox.checked;
          if (checkbox.checked) box.checked = false;
        });
      } else {
        const whiteHu = document.getElementById('white-hu') as HTMLInputElement | null;
        if (whiteHu) whiteHu.disabled = false;
        document.querySelectorAll<HTMLInputElement>('#black-defenses-list input[type="checkbox"]').forEach(box => {
          box.disabled = false;
        });
      }
    });
  });

  // Only one opening can be selected at a time
  document.querySelectorAll<HTMLInputElement>('#white-openings-list input[type="checkbox"]').forEach(function(checkbox) {
    checkbox.addEventListener('change', function (this: HTMLInputElement) {
      if (this.checked) {
        document.querySelectorAll<HTMLInputElement>('#white-openings-list input[type="checkbox"]').forEach(function(box) {
          if (box !== checkbox) box.checked = false;
        });
      }
    });
  });

  // Only one defense can be selected at a time
  document.querySelectorAll<HTMLInputElement>('#black-defenses-list input[type="checkbox"]').forEach(function(checkbox) {
    checkbox.addEventListener('change', function (this: HTMLInputElement) {
      if (this.checked) {
        document.querySelectorAll<HTMLInputElement>('#black-defenses-list input[type="checkbox"]').forEach(function(box) {
          if (box !== checkbox) box.checked = false;
        });
      }
    });
  });

  // Reset button logic for strategy tab
  const resetStrategyBtn = document.getElementById('resetStrategyBtn');
  if (resetStrategyBtn) {
    resetStrategyBtn.addEventListener('click', function () {
      document.querySelectorAll<HTMLInputElement>('#white-openings-list input[type="checkbox"]').forEach(function(box) {
        box.checked = false;
        box.disabled = false;
      });
      document.querySelectorAll<HTMLInputElement>('#black-defenses-list input[type="checkbox"]').forEach(function(box) {
        box.checked = false;
        box.disabled = false;
      });
    });
  }

  // Set button logic for strategy tab
  const setStrategyBtn = document.getElementById('setStrategyBtn');
  if (setStrategyBtn) {
    setStrategyBtn.addEventListener('click', function () {
      const opening = document.querySelector<HTMLInputElement>('#white-openings-list input[type="checkbox"]:checked');
      const defense = document.querySelector<HTMLInputElement>('#black-defenses-list input[type="checkbox"]:checked');
      let openingLabel = '';
      let defenseLabel = '';
      if (opening) {
        const label = opening.nextElementSibling;
        openingLabel = label ? (label as HTMLElement).textContent ?? '' : '';
      }
      if (defense) {
        const label = defense.nextElementSibling;
        defenseLabel = label ? (label as HTMLElement).textContent ?? '' : '';
      }
      const openingInfo = document.getElementById('player-info-opening');
      if (openingInfo) openingInfo.textContent = openingLabel;
      const defenseInfo = document.getElementById('player-info-defense');
      if (defenseInfo) defenseInfo.textContent = defenseLabel;
    });
  }

  // Set button logic: set player names in player-info box
  const setPlayersBtn = document.getElementById('setPlayersBtn');
  if (setPlayersBtn) {
    setPlayersBtn.addEventListener('click', function () {
      // Find checked white and black player
      const white = document.querySelector<HTMLInputElement>('#ai-model-list input[id^="white-"]:checked');
      const black = document.querySelector<HTMLInputElement>('#ai-model-list input[id^="black-"]:checked');
      // Map checkbox id to display name
      function getPlayerName(id: string): string {
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
      const playerInfoWhite = document.getElementById('player-info-white');
      if (playerInfoWhite) playerInfoWhite.textContent = whitePlayer;
      const playerInfoBlack = document.getElementById('player-info-black');
      if (playerInfoBlack) playerInfoBlack.textContent = blackPlayer;
    });
  }

  // Reset button logic for players tab
  const resetPlayersBtn = document.getElementById('resetPlayersBtn');
  if (resetPlayersBtn) {
    resetPlayersBtn.addEventListener('click', function () {
      // Uncheck and enable all player selection checkboxes
      document.querySelectorAll<HTMLInputElement>('#ai-model-list input[type="checkbox"]').forEach(box => {
        box.checked = false;
        box.disabled = false;
      });
      // Optionally clear player info display
      const playerInfoWhite = document.getElementById('player-info-white');
      if (playerInfoWhite) playerInfoWhite.textContent = '';
      const playerInfoBlack = document.getElementById('player-info-black');
      if (playerInfoBlack) playerInfoBlack.textContent = '';
    });
  }
});