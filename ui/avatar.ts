import { createAvatar } from '@dicebear/core';
import { pixelArt } from '@dicebear/collection';

const avatarIds = [
  'rook', 'knight', 'bishop', 'queen', 'king', 'pawn',
  'castle', 'crown', 'gambit', 'blitz', 'check', 'mate'
];

declare global {
  interface Window {
    chessAvatars: {
      ids: string[];
      dataUri: (avatarId?: string) => string;
    };
  }
}

window.chessAvatars = {
  ids: avatarIds,
  dataUri(avatarId) {
    const seed = avatarIds.includes(avatarId || '') ? avatarId! : avatarIds[0];
    return createAvatar(pixelArt, { seed }).toDataUri();
  }
};