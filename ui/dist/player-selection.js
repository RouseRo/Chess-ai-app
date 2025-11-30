"use strict";
document.addEventListener('DOMContentLoaded', function () {
    // Debug: Log when DOM is loaded
    console.debug('player-selection.ts: DOMContentLoaded');
    // Show Players tab panel logic
    function showPlayersTabPanel() {
        console.debug('player-selection.ts: showPlayersTabPanel called');
        document.querySelectorAll('.tab-content').forEach(el => {
            el.style.display = 'none';
        });
        const playersTab = document.getElementById('players-tab');
        if (playersTab)
            playersTab.style.display = 'block';
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        const tabBtn = document.querySelector('.tab-btn:nth-child(2)');
        if (tabBtn)
            tabBtn.classList.add('active');
    }
    // Only one checkbox per White column
    document.querySelectorAll('#ai-model-list input[id^="white-"]').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            if (checkbox.checked) {
                document.querySelectorAll('#ai-model-list input[id^="white-"]').forEach(function (box) {
                    if (box !== checkbox)
                        box.checked = false;
                });
            }
            if (checkbox.id === 'white-hu') {
                const blackHu = document.getElementById('black-hu');
                if (blackHu)
                    blackHu.disabled = checkbox.checked;
                document.querySelectorAll('#white-openings-list input[type="checkbox"]').forEach(box => {
                    box.disabled = checkbox.checked;
                    if (checkbox.checked)
                        box.checked = false;
                });
            }
            else {
                const blackHu = document.getElementById('black-hu');
                if (blackHu)
                    blackHu.disabled = false;
                document.querySelectorAll('#white-openings-list input[type="checkbox"]').forEach(box => {
                    box.disabled = false;
                });
            }
        });
    });
    // Only one checkbox per Black column
    document.querySelectorAll('#ai-model-list input[id^="black-"]').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            if (checkbox.checked) {
                document.querySelectorAll('#ai-model-list input[id^="black-"]').forEach(function (box) {
                    if (box !== checkbox)
                        box.checked = false;
                });
            }
            if (checkbox.id === 'black-hu') {
                const whiteHu = document.getElementById('white-hu');
                if (whiteHu)
                    whiteHu.disabled = checkbox.checked;
                document.querySelectorAll('#black-defenses-list input[type="checkbox"]').forEach(box => {
                    box.disabled = checkbox.checked;
                    if (checkbox.checked)
                        box.checked = false;
                });
            }
            else {
                const whiteHu = document.getElementById('white-hu');
                if (whiteHu)
                    whiteHu.disabled = false;
                document.querySelectorAll('#black-defenses-list input[type="checkbox"]').forEach(box => {
                    box.disabled = false;
                });
            }
        });
    });
    // Only one opening can be selected at a time
    document.querySelectorAll('#white-openings-list input[type="checkbox"]').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            if (this.checked) {
                document.querySelectorAll('#white-openings-list input[type="checkbox"]').forEach(function (box) {
                    if (box !== checkbox)
                        box.checked = false;
                });
            }
        });
    });
    // Only one defense can be selected at a time
    document.querySelectorAll('#black-defenses-list input[type="checkbox"]').forEach(function (checkbox) {
        checkbox.addEventListener('change', function () {
            if (this.checked) {
                document.querySelectorAll('#black-defenses-list input[type="checkbox"]').forEach(function (box) {
                    if (box !== checkbox)
                        box.checked = false;
                });
            }
        });
    });
    // Reset button logic for strategy tab
    const resetStrategyBtn = document.getElementById('resetStrategyBtn');
    if (resetStrategyBtn) {
        resetStrategyBtn.addEventListener('click', function () {
            document.querySelectorAll('#white-openings-list input[type="checkbox"]').forEach(function (box) {
                box.checked = false;
                box.disabled = false;
            });
            document.querySelectorAll('#black-defenses-list input[type="checkbox"]').forEach(function (box) {
                box.checked = false;
                box.disabled = false;
            });
        });
    }
    // Set button logic for strategy tab
    const setStrategyBtn = document.getElementById('setStrategyBtn');
    if (setStrategyBtn) {
        setStrategyBtn.addEventListener('click', function () {
            var _a, _b;
            const opening = document.querySelector('#white-openings-list input[type="checkbox"]:checked');
            const defense = document.querySelector('#black-defenses-list input[type="checkbox"]:checked');
            let openingLabel = '';
            let defenseLabel = '';
            if (opening) {
                const label = opening.nextElementSibling;
                openingLabel = label ? (_a = label.textContent) !== null && _a !== void 0 ? _a : '' : '';
            }
            if (defense) {
                const label = defense.nextElementSibling;
                defenseLabel = label ? (_b = label.textContent) !== null && _b !== void 0 ? _b : '' : '';
            }
            const openingInfo = document.getElementById('player-info-opening');
            if (openingInfo)
                openingInfo.textContent = openingLabel;
            const defenseInfo = document.getElementById('player-info-defense');
            if (defenseInfo)
                defenseInfo.textContent = defenseLabel;
        });
    }
    // Set button logic: set player names in player-info box
    const setPlayersBtn = document.getElementById('setPlayersBtn');
    if (setPlayersBtn) {
        setPlayersBtn.addEventListener('click', function () {
            // Find checked white and black player
            const white = document.querySelector('#ai-model-list input[id^="white-"]:checked');
            const black = document.querySelector('#ai-model-list input[id^="black-"]:checked');
            // Map checkbox id to display name
            function getPlayerName(id) {
                if (!id)
                    return '';
                if (id === 'hu')
                    return 'Human';
                if (id === 'm1')
                    return 'openai/gpt-4o';
                if (id === 'm2')
                    return 'deepseek/deepseek-chat-v3.1';
                if (id === 'm3')
                    return 'google/gemini-2.5-pro';
                if (id === 'm4')
                    return 'anthropic/claude-3-opus';
                if (id === 'm5')
                    return 'meta-llama/llama-3-70b-instruct';
                if (id === 's1')
                    return 'Skill level: 5';
                if (id === 's2')
                    return 'Skill level: 10';
                if (id === 's3')
                    return 'Skill level: 20';
                return id;
            }
            let whitePlayer = white ? getPlayerName(white.id.replace('white-', '')) : '';
            let blackPlayer = black ? getPlayerName(black.id.replace('black-', '')) : '';
            const playerInfoWhite = document.getElementById('player-info-white');
            if (playerInfoWhite)
                playerInfoWhite.textContent = whitePlayer;
            const playerInfoBlack = document.getElementById('player-info-black');
            if (playerInfoBlack)
                playerInfoBlack.textContent = blackPlayer;
        });
    }
    // Reset button logic for players tab
    const resetPlayersBtn = document.getElementById('resetPlayersBtn');
    if (resetPlayersBtn) {
        resetPlayersBtn.addEventListener('click', function () {
            // Uncheck and enable all player selection checkboxes
            document.querySelectorAll('#ai-model-list input[type="checkbox"]').forEach(box => {
                box.checked = false;
                box.disabled = false;
            });
            // Optionally clear player info display
            const playerInfoWhite = document.getElementById('player-info-white');
            if (playerInfoWhite)
                playerInfoWhite.textContent = '';
            const playerInfoBlack = document.getElementById('player-info-black');
            if (playerInfoBlack)
                playerInfoBlack.textContent = '';
        });
    }
});
