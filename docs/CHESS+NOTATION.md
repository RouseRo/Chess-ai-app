# Chess Notation and FEN Explained

This document provides a brief overview of the two main types of notation used in this chess application: Algebraic Notation for moves and Forsyth-Edwards Notation (FEN) for board positions.

## Algebraic Notation (for Moves)

Algebraic notation is the standard way to record and describe chess moves. This application uses a simplified version for move input called **UCI (Universal Chess Interface)** notation.

### UCI Notation (e.g., `e2e4`)

This is the most straightforward format and the one you use to input manual moves in the application.

-   It consists of four characters: the starting square followed by the ending square.
-   For example, moving a pawn from e2 to e4 is written as `e2e4`.
-   Promoting a pawn is specified by adding the piece it promotes to, for example, `e7e8q` promotes a pawn to a queen.

### Standard Algebraic Notation (SAN) (e.g., `Nf3`)

While the application uses UCI for input, logs and AI models often think in terms of SAN. It's more descriptive and less ambiguous.

-   **Piece:** Each piece has a letter (Pawn=no letter, `N`=Knight, `B`=Bishop, `R`=Rook, `Q`=Queen, `K`=King).
-   **Action:** A capture is marked with an `x`.
-   **Destination:** The square the piece moves to.
-   **Special Moves:** Check is `+`, checkmate is `#`, kingside castling is `O-O`, and queenside castling is `O-O-O`.

**Example:** `Nf3` means a Knight moves to the f3 square. `Bxc6+` means a Bishop captures a piece on c6 and delivers a check.

---

## Forsyth-Edwards Notation (FEN) (for Positions)

FEN is a standard for describing a particular board position, all in one line of text. It's used in this application to load practice positions and to log the state of the game after each move.

A FEN string has six fields, each separated by a space.

**Example:** The starting position in chess is represented as:
`rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1`

### The 6 FEN Fields

1.  **Piece Placement:**
    -   This describes the position of all pieces on the board.
    -   It starts from rank 8 and goes down to rank 1.
    -   A `/` separates each rank.
    -   White pieces are uppercase (`R`, `N`, `B`, `Q`, `K`, `P`), and black pieces are lowercase (`r`, `n`, `b`, `q`, `k`, `p`).
    -   Numbers represent consecutive empty squares on a rank. `8` means an entire rank is empty.

2.  **Active Color:**
    -   `w`: It is White's turn to move.
    -   `b`: It is Black's turn to move.

3.  **Castling Availability:**
    -   This indicates who can still castle and on which side.
    -   `K`: White can castle kingside.
    -   `Q`: White can castle queenside.
    -   `k`: Black can castle kingside.
    -   `q`: Black can castle queenside.
    -   `-`: No castling is possible for anyone.
    -   A value of `Kq` means White can castle kingside and Black can castle queenside.

4.  **En Passant Target Square:**
    -   If a pawn has just moved two squares, this is the square *behind* it that can be captured.
    -   If there is no en passant possibility, this is a hyphen (`-`).

5.  **Halfmove Clock:**
    -   The number of half-moves (or single moves by either player) since the last capture or pawn advance.
    -   This is used to enforce the 50-move rule.

6.  **Fullmove Number:**
    -   The number of the current move. It starts at `1` and is incremented after Black completes their move.