# Chess AI Application

## Overview

A command-line chess application that lets you play against various AI models and Stockfish engines. Features include game saving/loading, player statistics tracking, and an interactive "Ask a Chess Expert" feature.

## Installation

### Prerequisites

-   Python 3.12 or later
-   Pip package manager

### Setup

1.  Clone the repository:
    ````bash
    git clone <repository-url>
    cd Chess-ai-app
    ````

2.  Create and activate a virtual environment:
    ````bash
    # On Windows
    python -m venv .venv
    .venv\Scripts\activate

    # On macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ````

3.  Install dependencies:
    ````bash
    pip install -r requirements.txt
    ````

## Features

### Main Menu

-   **Play a New Game**: Start a fresh chess game against an AI opponent or another human.
-   **Load a Saved Game**: Continue a previously saved match.
-   **Load a Practice Position**: Study specific board configurations.
-   **View Player Stats**: Check your win/loss/draw statistics.
-   **Ask a Chess Expert**: Get advice from the Chess AI.

### Game Options

-   Choose from multiple AI models (GPT-4o, Claude, Gemini, etc.).
-   Select different Stockfish engine configurations (casual to powerful).
-   Apply classic chess openings and defenses for AI players.
-   Save games for later continuation.

## Usage

To run the application, execute the following command from the root directory:

````bash
python -m src.main
````
