// Declare Chessboard as a global variable for TypeScript
declare var Chessboard: any;

document.addEventListener('DOMContentLoaded', function () {
  // Initialize chessboard with onDrop handler
  const board = Chessboard('board', {
    draggable: true,
    onDrop: function (source: string, target: string, piece: string, newPos: any, oldPos: any, orientation: string) {
      const move = source + '-' + target;
      // Log move to the Game tab panel (not expert tab)
      const gameContent = document.getElementById('game-content');
      if (gameContent) {
        const logEntry = document.createElement('div');
        logEntry.textContent = `Move: ${move}`;
        gameContent.appendChild(logEntry);
      }
      // Return 'snapback' to allow normal board behavior
      return 'snapback';
    }
  });
});