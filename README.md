# Unblock Me - https://unblock-me-game.vercel.app/

A custom, playable sliding block puzzle game built with React. Design your own puzzles with a drag-and-drop map builder, then solve them by sliding blocks to free the red target piece.

![Built with React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=white)
![Styled with Glassmorphism](https://img.shields.io/badge/Design-Glassmorphism-blueviolet)
![Deployed on Vercel](https://img.shields.io/badge/Deployed-Vercel-black?logo=vercel)

## How It Works

The game takes place on a 6×6 grid. Horizontal blocks can only slide left and right. Vertical blocks can only slide up and down. The goal is to slide the **red target block** out through the exit on the right side of the board.

## Features

### Map Builder
- **Drag-and-drop** pieces from the palette directly onto the grid
- **6 piece types**: Target (red, horizontal, length 2), Horizontal 2, Horizontal 3, Vertical 2, Vertical 3, and Obstacle (black, 1×1, immovable)
- **Live letter editor** with per-character input boxes that update the grid in real time as you type
- **Reposition** any placed block by dragging it to a new location
- **Delete** blocks by dragging them off the grid
- **Save and load** maps by name

### Play Mode
- **Drag** blocks or **click + arrow keys** to slide them
- Move counter tracks each action (one move per drag, regardless of distance)
- **Undo** any move (decrements the counter)
- **Restart** to reset the puzzle to its initial state
- Win detection when the red block exits the board

### Visual Design
- Glassmorphic UI inspired by Apple VisionOS
- Animated parallax background with luminous gradient orbs that track cursor movement
- Frosted glass panels, buttons, and cards with backdrop blur
- Glass reflection and refraction overlays on every block that shift with the cursor
- Seamless block tiles with subtle glass divider lines between connected cells
- Space Grotesk typography throughout

## Getting Started

### Prerequisites
- Node.js 18+
- npm

### Install and Run

```bash
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

### Deploy to Vercel

1. Push to a GitHub repository
2. Import the repo at [vercel.com](https://vercel.com)
3. Deploy — Vercel auto-detects Vite and handles the rest

## Controls

| Action | Input |
|---|---|
| Place a piece | Drag from palette onto grid |
| Move a piece (builder) | Drag it to a new cell |
| Delete a piece | Drag it off the grid |
| Edit letters | Click a block on the grid or in the placed list |
| Slide a block (play) | Click and drag, or click then use arrow keys |
| Undo | Click ↩ Undo button |
| Restart | Click ⟳ Restart button |

## Tech Stack

- **React 18** with hooks
- **Vite** for dev/build
- **Space Grotesk** (Google Fonts)
- **Vercel Analytics** (optional)

## License

MIT
