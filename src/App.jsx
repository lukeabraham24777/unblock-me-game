import { useState, useCallback, useEffect, useRef } from "react";
import { Analytics } from "@vercel/analytics/react";
import { GlowingEffect } from "@/components/ui/glowing-effect";

const GRID_SIZE = 6;
const CELL_PX = 72;
const GAP = 0;
const BOARD_PAD = 6;

const emptyGrid = () => Array.from({ length: GRID_SIZE }, () => Array(GRID_SIZE).fill(null));

const MODES = { BUILD: "build", PLAY: "play" };

let idCounter = 1;
const uid = () => "b" + idCounter++;

function getBlockCells(block) {
  const cells = [];
  const len = block.isObstacle ? 1 : block.length;
  for (let i = 0; i < len; i++) {
    if (block.orientation === "horizontal") {
      cells.push({ row: block.row, col: block.col + i });
    } else {
      cells.push({ row: block.row + i, col: block.col });
    }
  }
  return cells;
}

function isValidPlacement(block, blocks, excludeId = null) {
  const cells = getBlockCells(block);
  for (const c of cells) {
    if (c.row < 0 || c.row >= GRID_SIZE || c.col < 0 || c.col >= GRID_SIZE) return false;
  }
  for (const other of blocks) {
    if (other.id === excludeId) continue;
    const otherCells = getBlockCells(other);
    for (const c of cells) {
      for (const oc of otherCells) {
        if (c.row === oc.row && c.col === oc.col) return false;
      }
    }
  }
  return true;
}

function buildGrid(blocks) {
  const grid = emptyGrid();
  for (const b of blocks) {
    const cells = getBlockCells(b);
    cells.forEach((c, i) => {
      if (c.row >= 0 && c.row < GRID_SIZE && c.col >= 0 && c.col < GRID_SIZE) {
        const letter = b.isObstacle ? (b.letters[0] || "") : (b.letters[i] || "");
        grid[c.row][c.col] = { blockId: b.id, letter, isTarget: b.isTarget, isObstacle: b.isObstacle };
      }
    });
  }
  return grid;
}

const PIECE_TEMPLATES = [
  { label: "Target", length: 2, orientation: "horizontal", isTarget: true, isObstacle: false, color: "rgba(220,50,47,0.85)", accent: "rgba(255,90,80,0.7)" },
  { label: "H2", length: 2, orientation: "horizontal", isTarget: false, isObstacle: false, color: "rgba(60,140,220,0.8)", accent: "rgba(100,180,255,0.6)" },
  { label: "H3", length: 3, orientation: "horizontal", isTarget: false, isObstacle: false, color: "rgba(60,140,220,0.8)", accent: "rgba(100,180,255,0.6)" },
  { label: "V2", length: 2, orientation: "vertical", isTarget: false, isObstacle: false, color: "rgba(60,140,220,0.8)", accent: "rgba(100,180,255,0.6)" },
  { label: "V3", length: 3, orientation: "vertical", isTarget: false, isObstacle: false, color: "rgba(60,140,220,0.8)", accent: "rgba(100,180,255,0.6)" },
  { label: "Wall", length: 1, orientation: "horizontal", isTarget: false, isObstacle: true, color: "rgba(20,20,40,0.9)", accent: "rgba(80,80,100,0.5)" },
];

const MINI = 28;
const MINI_GAP = 2;

function PieceFigure({ tmpl, mini = MINI }) {
  const len = tmpl.isObstacle ? 1 : tmpl.length;
  const isH = tmpl.orientation === "horizontal";
  const cols = isH ? len : 1;
  const rows = isH ? 1 : len;
  return (
    <div style={{
      display: "grid",
      gridTemplateColumns: `repeat(${cols}, ${mini}px)`,
      gridTemplateRows: `repeat(${rows}, ${mini}px)`,
      gap: `${MINI_GAP}px`,
    }}>
      {Array.from({ length: len }).map((_, i) => (
        <div key={i} style={{
          width: mini, height: mini, borderRadius: 6,
          background: tmpl.color,
          border: `1px solid ${tmpl.accent}`,
          boxShadow: `inset 0 1px 0 rgba(255,255,255,0.2), 0 1px 4px rgba(0,0,0,0.3)`,
        }} />
      ))}
    </div>
  );
}

const savedMapsStore = [];

/* ── Glassmorphic Style Tokens ── */
const GS = {
  glass: "rgba(255,255,255,0.06)",
  glassBorder: "rgba(255,255,255,0.12)",
  glassHover: "rgba(255,255,255,0.1)",
  glassStrong: "rgba(255,255,255,0.09)",
  glassInput: "rgba(0,0,0,0.35)",
  inputBorder: "rgba(255,255,255,0.1)",
  blur: "blur(24px)",
  blurHeavy: "blur(40px)",
  text: "rgba(255,255,255,0.92)",
  textMuted: "rgba(255,255,255,0.45)",
  textDim: "rgba(255,255,255,0.3)",
  accentWarm: "#ff9f43",
  accentRed: "#ff6b6b",
  accentBlue: "#74b9ff",
  gridBg: "rgba(255,255,255,0.04)",
  gridBorder: "rgba(255,255,255,0.08)",
  emptyCell: "rgba(255,255,255,0.04)",
  emptyCellBorder: "rgba(255,255,255,0.06)",
  blockBlue: "rgba(52,131,235,0.82)",
  blockRed: "rgba(225,55,55,0.85)",
  blockObs: "rgba(15,15,30,0.92)",
  selectedGlow: "rgba(255,159,67,0.6)",
  shadowDeep: "0 12px 48px rgba(0,0,0,0.4), 0 2px 12px rgba(0,0,0,0.2)",
  shadowCard: "0 8px 32px rgba(0,0,0,0.35), inset 0 0.5px 0 rgba(255,255,255,0.12)",
  radius: "16px",
  radiusSm: "10px",
};

export default function UnblockMe() {
  const [mode, setMode] = useState(MODES.BUILD);
  const [blocks, setBlocks] = useState([]);
  const [selectedBlockId, setSelectedBlockId] = useState(null);
  const [moveCount, setMoveCount] = useState(0);
  const [history, setHistory] = useState([]);
  const [won, setWon] = useState(false);
  const [savedMaps, setSavedMaps] = useState([]);
  const [mapName, setMapName] = useState("");
  const [showSavePanel, setShowSavePanel] = useState(false);
  const [showLoadPanel, setShowLoadPanel] = useState(false);

  const [editingBlockId, setEditingBlockId] = useState(null);
  const [editLetters, setEditLetters] = useState("");

  const [draggingTemplate, setDraggingTemplate] = useState(null);
  const [draggingExisting, setDraggingExisting] = useState(null);
  const [dragGhost, setDragGhost] = useState(null);
  const [hoverCell, setHoverCell] = useState(null);
  const gridRef = useRef(null);
  const bgRef = useRef(null);

  const hasTarget = blocks.some((b) => b.isTarget);
  const targetBlock = blocks.find((b) => b.isTarget);
  const exitRow = targetBlock ? targetBlock.row : -1;
  const grid = buildGrid(blocks);

  /* ── Parallax mouse tracker ── */
  const [mousePos, setMousePos] = useState({ x: 0.5, y: 0.5 });
  useEffect(() => {
    const handler = (e) => {
      setMousePos({ x: e.clientX / window.innerWidth, y: e.clientY / window.innerHeight });
    };
    window.addEventListener("mousemove", handler);
    return () => window.removeEventListener("mousemove", handler);
  }, []);

  const pixelToCell = useCallback((px, py) => {
    const col = Math.floor((px - BOARD_PAD) / (CELL_PX + GAP));
    const row = Math.floor((py - BOARD_PAD) / (CELL_PX + GAP));
    return {
      row: Math.max(0, Math.min(GRID_SIZE - 1, row)),
      col: Math.max(0, Math.min(GRID_SIZE - 1, col)),
    };
  }, []);

  const getGridXY = useCallback((clientX, clientY) => {
    if (!gridRef.current) return null;
    const rect = gridRef.current.getBoundingClientRect();
    const x = clientX - rect.left;
    const y = clientY - rect.top;
    if (x < 0 || y < 0 || x > rect.width || y > rect.height) return null;
    return { x, y };
  }, []);

  // ─── BUILD: palette drag ───
  const onPaletteDragStart = (tmpl, e) => {
    if (tmpl.isTarget && hasTarget) return;
    setDraggingTemplate(tmpl);
    setDragGhost({ x: e.clientX, y: e.clientY });
    e.preventDefault();
  };

  useEffect(() => {
    if (!draggingTemplate && !draggingExisting) return;
    const activeTmpl = draggingTemplate || (draggingExisting ? {
      length: draggingExisting.isObstacle ? 1 : draggingExisting.length,
      orientation: draggingExisting.orientation,
      isTarget: draggingExisting.isTarget,
      isObstacle: draggingExisting.isObstacle,
    } : null);
    if (!activeTmpl) return;

    const onMove = (e) => {
      setDragGhost({ x: e.clientX, y: e.clientY });
      const gxy = getGridXY(e.clientX, e.clientY);
      if (gxy) {
        setHoverCell(pixelToCell(gxy.x, gxy.y));
      } else {
        setHoverCell(null);
      }
    };
    const onUp = (e) => {
      const gxy = getGridXY(e.clientX, e.clientY);

      if (draggingExisting) {
        if (gxy) {
          const cell = pixelToCell(gxy.x, gxy.y);
          const movedBlock = { ...draggingExisting, row: cell.row, col: cell.col };
          if (isValidPlacement(movedBlock, blocks, draggingExisting.id)) {
            setBlocks((prev) => prev.map((b) => b.id === draggingExisting.id ? movedBlock : b));
            setEditingBlockId(draggingExisting.id);
            setEditLetters(draggingExisting.letters.trimEnd());
          } else {
            setBlocks((prev) => prev.map((b) => b.id === draggingExisting.id ? draggingExisting : b));
          }
        } else {
          setBlocks((prev) => prev.filter((b) => b.id !== draggingExisting.id));
          if (selectedBlockId === draggingExisting.id) setSelectedBlockId(null);
          if (editingBlockId === draggingExisting.id) setEditingBlockId(null);
        }
        setDraggingExisting(null);
      } else if (draggingTemplate) {
        if (gxy) {
          const cell = pixelToCell(gxy.x, gxy.y);
          const newBlock = {
            id: uid(),
            length: draggingTemplate.isObstacle ? 1 : draggingTemplate.length,
            orientation: draggingTemplate.orientation,
            row: cell.row, col: cell.col,
            letters: "",
            isTarget: draggingTemplate.isTarget,
            isObstacle: draggingTemplate.isObstacle,
          };
          if (isValidPlacement(newBlock, blocks)) {
            setBlocks((prev) => [...prev, newBlock]);
            setEditingBlockId(newBlock.id);
            setEditLetters(newBlock.letters.trimEnd());
          }
        }
        setDraggingTemplate(null);
      }

      setDragGhost(null);
      setHoverCell(null);
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => { window.removeEventListener("mousemove", onMove); window.removeEventListener("mouseup", onUp); };
  }, [draggingTemplate, draggingExisting, blocks, getGridXY, pixelToCell, selectedBlockId, editingBlockId]);

  const removeBlock = (id) => {
    setBlocks((prev) => prev.filter((b) => b.id !== id));
    if (selectedBlockId === id) setSelectedBlockId(null);
    if (editingBlockId === id) setEditingBlockId(null);
  };

  const saveLetters = () => {
    if (!editingBlockId) return;
    setBlocks((prev) =>
      prev.map((b) => b.id === editingBlockId
        ? { ...b, letters: editLetters.toUpperCase().padEnd(b.length, " ").slice(0, b.length) }
        : b
      )
    );
    setEditingBlockId(null);
  };

  const clearAll = () => { setBlocks([]); setSelectedBlockId(null); setEditingBlockId(null); };

  // ─── SAVE / LOAD ───
  const saveMap = () => {
    if (!mapName.trim()) return;
    if (!hasTarget) { alert("Place a target (red) block first."); return; }
    savedMapsStore.push({ name: mapName.trim(), blocks: JSON.parse(JSON.stringify(blocks)), id: Date.now() });
    setSavedMaps([...savedMapsStore]);
    setMapName("");
    setShowSavePanel(false);
  };
  const loadMap = (entry) => {
    setBlocks(JSON.parse(JSON.stringify(entry.blocks)));
    setMode(MODES.BUILD);
    setShowLoadPanel(false);
    resetPlay();
  };
  const deleteMap = (id) => {
    const idx = savedMapsStore.findIndex((m) => m.id === id);
    if (idx !== -1) savedMapsStore.splice(idx, 1);
    setSavedMaps([...savedMapsStore]);
  };

  // ─── PLAY ───
  const startPlay = () => {
    if (!hasTarget) { alert("Place a target (red) block first!"); return; }
    resetPlay();
    setMode(MODES.PLAY);
  };
  const resetPlay = () => { setMoveCount(0); setHistory([]); setWon(false); setSelectedBlockId(null); };
  const backToBuild = () => { setMode(MODES.BUILD); resetPlay(); };

  const undoMove = () => {
    if (history.length === 0) return;
    setBlocks(history[history.length - 1]);
    setHistory((h) => h.slice(0, -1));
    setMoveCount((c) => c - 1);
    setWon(false);
  };

  const restartPuzzle = () => {
    if (history.length === 0) return;
    setBlocks(history[0]);
    setHistory([]);
    setMoveCount(0);
    setWon(false);
  };

  // ─── Single step move ───
  const tryMoveBlock = useCallback((blockId, direction, currentBlocks, eRow) => {
    const idx = currentBlocks.findIndex((b) => b.id === blockId);
    if (idx === -1) return null;
    const block = currentBlocks[idx];
    if (block.isObstacle) return null;

    let dr = 0, dc = 0;
    if (direction === "left" && block.orientation === "horizontal") dc = -1;
    else if (direction === "right" && block.orientation === "horizontal") dc = 1;
    else if (direction === "up" && block.orientation === "vertical") dr = -1;
    else if (direction === "down" && block.orientation === "vertical") dr = 1;
    else return null;

    const moved = { ...block, row: block.row + dr, col: block.col + dc };

    if (moved.isTarget && moved.orientation === "horizontal" && moved.row === eRow) {
      const headCol = moved.col + moved.length - 1;
      if (headCol >= GRID_SIZE) {
        const newBlocks = [...currentBlocks];
        newBlocks[idx] = moved;
        return { blocks: newBlocks, won: true };
      }
    }

    if (!isValidPlacement(moved, currentBlocks, block.id)) return null;

    const newBlocks = [...currentBlocks];
    newBlocks[idx] = moved;
    return { blocks: newBlocks, won: false };
  }, []);

  // ─── PLAY: drag (1 move per full drag) ───
  const handlePlayMouseDown = (row, col, e) => {
    if (mode !== MODES.PLAY || won) return;
    const cell = grid[row][col];
    if (!cell || cell.isObstacle) return;
    const blockId = cell.blockId;
    setSelectedBlockId(blockId);
    e.preventDefault();

    const snapshotBefore = blocks.map((b) => ({ ...b }));
    const origBlock = snapshotBefore.find((b) => b.id === blockId);
    if (!origBlock) return;

    let currentBlocks = blocks.map((b) => ({ ...b }));
    let moved = false;
    let wonFlag = false;
    const startX = e.clientX;
    const startY = e.clientY;
    const exitR = exitRow;

    const onMove = (ev) => {
      if (wonFlag) return;
      const dx = ev.clientX - startX;
      const dy = ev.clientY - startY;

      const cur = currentBlocks.find((b) => b.id === blockId);
      if (!cur) return;

      let targetPos;
      if (cur.orientation === "horizontal") {
        targetPos = origBlock.col + Math.round(dx / (CELL_PX + GAP));
      } else {
        targetPos = origBlock.row + Math.round(dy / (CELL_PX + GAP));
      }

      const currentPos = cur.orientation === "horizontal" ? cur.col : cur.row;
      if (targetPos === currentPos) return;

      const dir = cur.orientation === "horizontal"
        ? (targetPos > currentPos ? "right" : "left")
        : (targetPos > currentPos ? "down" : "up");
      const steps = Math.abs(targetPos - currentPos);

      let tempBlocks = currentBlocks.map((b) => ({ ...b }));
      for (let s = 0; s < steps; s++) {
        const result = tryMoveBlock(blockId, dir, tempBlocks, exitR);
        if (!result) break;
        tempBlocks = result.blocks;
        moved = true;
        if (result.won) {
          wonFlag = true;
          currentBlocks = tempBlocks;
          setBlocks([...tempBlocks]);
          setHistory((h) => [...h, snapshotBefore]);
          setMoveCount((c) => c + 1);
          setTimeout(() => setWon(true), 100);
          break;
        }
      }
      if (!wonFlag) {
        currentBlocks = tempBlocks;
        setBlocks([...tempBlocks]);
      }
    };

    const onUp = () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
      if (wonFlag) return;
      if (moved) {
        setHistory((h) => [...h, snapshotBefore]);
        setMoveCount((c) => c + 1);
      }
    };

    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  };

  // ─── Keyboard play ───
  useEffect(() => {
    if (mode !== MODES.PLAY || !selectedBlockId || won) return;
    const handler = (e) => {
      const map = { ArrowLeft: "left", ArrowRight: "right", ArrowUp: "up", ArrowDown: "down" };
      const dir = map[e.key];
      if (!dir) return;
      e.preventDefault();
      setBlocks((prev) => {
        const result = tryMoveBlock(selectedBlockId, dir, prev, exitRow);
        if (!result) return prev;
        setHistory((h) => [...h, prev]);
        setMoveCount((c) => c + 1);
        if (result.won) setTimeout(() => setWon(true), 100);
        return result.blocks;
      });
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [mode, selectedBlockId, won, tryMoveBlock, exitRow]);

  // ─── Cell visuals (glassmorphic) ───
  const cellColor = (row, col) => {
    const cell = grid[row][col];
    if (!cell) return GS.emptyCell;
    if (cell.isObstacle) return GS.blockObs;
    if (cell.isTarget) return GS.blockRed;
    return GS.blockBlue;
  };

  const INSET = 0;
  const cellInset = (row, col) => {
    return { top: 0, right: 0, bottom: 0, left: 0 };
  };

  // Determine which edges of this cell need a glass divider (interior seams)
  const cellDividers = (row, col) => {
    const cell = grid[row][col];
    if (!cell || cell.isObstacle) return { top: false, left: false };
    const block = blocks.find((b) => b.id === cell.blockId);
    if (!block) return { top: false, left: false };
    const cells = getBlockCells(block);
    const idx = cells.findIndex((c) => c.row === row && c.col === col);
    return {
      top: block.orientation === "vertical" && idx > 0,
      left: block.orientation === "horizontal" && idx > 0,
    };
  };

  // Determine outer border radius for this cell within its block
  const cellRadius = (row, col) => {
    const cell = grid[row][col];
    if (!cell || cell.isObstacle) return "8px";
    const block = blocks.find((b) => b.id === cell.blockId);
    if (!block) return "8px";
    const cells = getBlockCells(block);
    const idx = cells.findIndex((c) => c.row === row && c.col === col);
    const R = 8;
    if (block.orientation === "horizontal") {
      const isFirst = idx === 0;
      const isLast = idx === cells.length - 1;
      return `${isFirst ? R : 0}px ${isLast ? R : 0}px ${isLast ? R : 0}px ${isFirst ? R : 0}px`;
    } else {
      const isFirst = idx === 0;
      const isLast = idx === cells.length - 1;
      return `${isFirst ? R : 0}px ${isFirst ? R : 0}px ${isLast ? R : 0}px ${isLast ? R : 0}px`;
    }
  };

  const isSelectedCell = (row, col) => {
    const cell = grid[row][col];
    return cell && cell.blockId === selectedBlockId;
  };

  // Per-edge border for block outlines (only outer edges get a border)
  const cellBorders = (row, col) => {
    const cell = grid[row][col];
    if (!cell) return null;
    if (cell.isObstacle) return { borderTop: "2px", borderRight: "2px", borderBottom: "2px", borderLeft: "2px" };
    const block = blocks.find((b) => b.id === cell.blockId);
    if (!block) return null;
    const cells = getBlockCells(block);
    const idx = cells.findIndex((c) => c.row === row && c.col === col);
    const W = "2px";
    const N = "0px";
    if (block.orientation === "horizontal") {
      return {
        borderTop: W,
        borderBottom: W,
        borderLeft: idx === 0 ? W : N,
        borderRight: idx === cells.length - 1 ? W : N,
      };
    } else {
      return {
        borderLeft: W,
        borderRight: W,
        borderTop: idx === 0 ? W : N,
        borderBottom: idx === cells.length - 1 ? W : N,
      };
    }
  };

  const activeDrag = draggingTemplate || (draggingExisting ? {
    length: draggingExisting.isObstacle ? 1 : draggingExisting.length,
    orientation: draggingExisting.orientation,
    isTarget: draggingExisting.isTarget,
    isObstacle: draggingExisting.isObstacle,
  } : null);

  const ghostCells = () => {
    if (!activeDrag || !hoverCell) return [];
    const len = activeDrag.isObstacle ? 1 : activeDrag.length;
    const cells = [];
    for (let i = 0; i < len; i++) {
      if (activeDrag.orientation === "horizontal") {
        cells.push({ row: hoverCell.row, col: hoverCell.col + i });
      } else {
        cells.push({ row: hoverCell.row + i, col: hoverCell.col });
      }
    }
    return cells;
  };

  const ghostValid = () => {
    if (!activeDrag || !hoverCell) return false;
    const testBlock = {
      id: draggingExisting ? draggingExisting.id : "__ghost__",
      length: activeDrag.isObstacle ? 1 : activeDrag.length,
      orientation: activeDrag.orientation,
      row: hoverCell.row, col: hoverCell.col,
      isTarget: activeDrag.isTarget, isObstacle: activeDrag.isObstacle,
    };
    return isValidPlacement(testBlock, blocks, draggingExisting ? draggingExisting.id : null);
  };

  const gc = ghostCells();
  const gv = ghostValid();

  /* ── Parallax offsets ── */
  const px1 = (mousePos.x - 0.5) * 30;
  const py1 = (mousePos.y - 0.5) * 30;
  const px2 = (mousePos.x - 0.5) * -20;
  const py2 = (mousePos.y - 0.5) * -20;

  return (
    <div style={{
      minHeight: "100vh",
      background: "#050510",
      fontFamily: "'Space Grotesk', 'SF Pro Display', -apple-system, sans-serif",
      color: GS.text,
      display: "flex", flexDirection: "column", alignItems: "center",
      padding: "24px",
      userSelect: "none",
      position: "relative",
      overflow: "hidden",
    }}>
      {/* ── Animated mesh gradient background ── */}
      <div style={{
        position: "fixed", inset: 0, zIndex: 0, overflow: "hidden", pointerEvents: "none",
      }}>
        {/* Orb 1 */}
        <div style={{
          position: "absolute",
          width: 700, height: 700,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(120,50,255,0.25) 0%, rgba(120,50,255,0) 70%)",
          top: "-10%", left: "-10%",
          transform: `translate(${px1}px, ${py1}px)`,
          transition: "transform 0.3s ease-out",
          filter: "blur(60px)",
        }} />
        {/* Orb 2 */}
        <div style={{
          position: "absolute",
          width: 600, height: 600,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255,100,60,0.2) 0%, rgba(255,100,60,0) 70%)",
          bottom: "-15%", right: "-5%",
          transform: `translate(${px2}px, ${py2}px)`,
          transition: "transform 0.3s ease-out",
          filter: "blur(50px)",
        }} />
        {/* Orb 3 */}
        <div style={{
          position: "absolute",
          width: 500, height: 500,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(50,180,255,0.15) 0%, rgba(50,180,255,0) 70%)",
          top: "40%", right: "20%",
          transform: `translate(${px1 * 0.5}px, ${py2 * 0.7}px)`,
          transition: "transform 0.3s ease-out",
          filter: "blur(40px)",
        }} />
        {/* Subtle noise grain */}
        <div style={{
          position: "absolute", inset: 0,
          backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E")`,
          backgroundSize: "200px 200px",
          opacity: 0.4,
        }} />
      </div>

      {/* ── Content layer ── */}
      <div style={{ position: "relative", zIndex: 1, display: "flex", flexDirection: "column", alignItems: "center", width: "100%" }}>

        {/* Title */}
        <h1 style={{
          fontSize: "38px", fontWeight: 700, letterSpacing: "6px", textTransform: "uppercase",
          margin: "0 0 2px 0",
          background: "linear-gradient(135deg, #ff6b6b 0%, #ffa502 40%, #ff6348 100%)",
          WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
          filter: "drop-shadow(0 0 20px rgba(255,107,107,0.3))",
        }}>
          Unblock Me
        </h1>
        <p style={{
          margin: "0 0 20px 0", fontSize: "11px", color: GS.textMuted,
          letterSpacing: "3px", textTransform: "uppercase", fontWeight: 500,
        }}>
          {mode === MODES.BUILD ? "Map Builder" : "Play Mode"}
        </p>

        {/* Top bar */}
        <div style={{ display: "flex", gap: "8px", marginBottom: "20px", flexWrap: "wrap", justifyContent: "center" }}>
          {mode === MODES.BUILD ? (
            <>
              <GlassBtn onClick={startPlay} accent>▶ Play</GlassBtn>
              <GlassBtn onClick={() => { setSavedMaps([...savedMapsStore]); setShowSavePanel(!showSavePanel); setShowLoadPanel(false); }}>💾 Save</GlassBtn>
              <GlassBtn onClick={() => { setSavedMaps([...savedMapsStore]); setShowLoadPanel(!showLoadPanel); setShowSavePanel(false); }}>📂 Load</GlassBtn>
              <GlassBtn onClick={clearAll} danger>🗑 Clear</GlassBtn>
            </>
          ) : (
            <>
              <GlassBtn onClick={backToBuild}>← Builder</GlassBtn>
              <GlassBtn onClick={undoMove} disabled={history.length === 0}>↩ Undo</GlassBtn>
              <GlassBtn onClick={restartPuzzle} disabled={history.length === 0}>⟳ Restart</GlassBtn>
              <div style={{
                padding: "8px 20px",
                background: GS.glass,
                backdropFilter: GS.blur,
                WebkitBackdropFilter: GS.blur,
                borderRadius: GS.radiusSm,
                fontSize: "14px", fontWeight: 600,
                border: `1px solid ${GS.glassBorder}`,
                display: "flex", alignItems: "center", gap: "8px",
                boxShadow: "inset 0 0.5px 0 rgba(255,255,255,0.1)",
              }}>
                <span style={{ color: GS.textMuted, fontSize: "12px", letterSpacing: "1px", textTransform: "uppercase" }}>Moves</span>
                <span style={{ color: GS.accentWarm, fontSize: "22px", fontWeight: 700, fontVariantNumeric: "tabular-nums" }}>{moveCount}</span>
              </div>
            </>
          )}
        </div>

        {/* Save panel */}
        {showSavePanel && (
          <GlassPanel>
            <h3 style={{ margin: "0 0 10px", fontSize: "13px", fontWeight: 600, color: GS.accentWarm, letterSpacing: "2px", textTransform: "uppercase" }}>Save Map</h3>
            <div style={{ display: "flex", gap: "8px" }}>
              <input value={mapName} onChange={(e) => setMapName(e.target.value)} placeholder="Map name…"
                style={{ ...glassInputStyle, flex: 1 }} onKeyDown={(e) => e.key === "Enter" && saveMap()} />
              <GlassBtn onClick={saveMap} accent small>Save</GlassBtn>
            </div>
          </GlassPanel>
        )}

        {/* Load panel */}
        {showLoadPanel && (
          <GlassPanel>
            <h3 style={{ margin: "0 0 10px", fontSize: "13px", fontWeight: 600, color: GS.accentWarm, letterSpacing: "2px", textTransform: "uppercase" }}>Load Map</h3>
            {savedMaps.length === 0 ? (
              <p style={{ color: GS.textMuted, fontSize: "13px", margin: 0 }}>No saved maps yet.</p>
            ) : (
              <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "150px", overflowY: "auto" }}>
                {savedMaps.map((m) => (
                  <div key={m.id} style={{
                    display: "flex", justifyContent: "space-between", alignItems: "center",
                    background: GS.glassInput, borderRadius: GS.radiusSm, padding: "8px 12px",
                    border: `1px solid ${GS.inputBorder}`,
                  }}>
                    <span style={{ fontSize: "13px", fontWeight: 500 }}>{m.name}</span>
                    <div style={{ display: "flex", gap: "6px" }}>
                      <GlassBtn onClick={() => loadMap(m)} small accent>Load</GlassBtn>
                      <GlassBtn onClick={() => deleteMap(m.id)} small danger>✕</GlassBtn>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </GlassPanel>
        )}

        {/* Win overlay */}
        {won && (
          <div style={{
            position: "fixed", inset: 0,
            background: "rgba(5,5,16,0.85)",
            backdropFilter: GS.blurHeavy,
            WebkitBackdropFilter: GS.blurHeavy,
            zIndex: 999,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <div style={{
              background: GS.glassStrong,
              backdropFilter: GS.blurHeavy,
              WebkitBackdropFilter: GS.blurHeavy,
              border: `1px solid rgba(255,159,67,0.3)`,
              borderRadius: "24px",
              padding: "48px 56px", textAlign: "center",
              boxShadow: `0 0 80px rgba(255,159,67,0.15), ${GS.shadowDeep}`,
            }}>
              <div style={{ fontSize: "56px", marginBottom: "16px", filter: "drop-shadow(0 0 12px rgba(255,200,50,0.4))" }}>🎉</div>
              <h2 style={{
                margin: "0 0 8px", fontSize: "28px", fontWeight: 700, letterSpacing: "2px",
                background: "linear-gradient(135deg, #ff6b6b, #ffa502)",
                WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent",
              }}>Puzzle Solved!</h2>
              <p style={{ color: GS.textMuted, margin: "0 0 24px", fontSize: "16px" }}>
                Completed in <span style={{ color: GS.accentWarm, fontWeight: 700 }}>{moveCount}</span> move{moveCount !== 1 ? "s" : ""}
              </p>
              <div style={{ display: "flex", gap: "10px", justifyContent: "center" }}>
                <GlassBtn onClick={restartPuzzle} accent>⟳ Replay</GlassBtn>
                <GlassBtn onClick={backToBuild}>← Builder</GlassBtn>
              </div>
            </div>
          </div>
        )}

        <div style={{ display: "flex", gap: "24px", alignItems: "flex-start", flexWrap: "wrap", justifyContent: "center" }}>
          {/* Grid area */}
          <div style={{ position: "relative" }}>
            {/* Exit arrow */}
            {hasTarget && (
              <div style={{
                position: "absolute", right: -32,
                top: BOARD_PAD + exitRow * (CELL_PX + GAP) + CELL_PX / 2 - 14,
                width: 32, height: 28, display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "22px", color: GS.accentRed,
                filter: `drop-shadow(0 0 10px rgba(255,107,107,0.7))`,
                transition: "top 0.3s cubic-bezier(0.34,1.56,0.64,1)",
                animation: "pulseArrow 2s ease-in-out infinite",
              }}>➜</div>
            )}

            {/* Grid — frosted glass board */}
            <div ref={gridRef} style={{
              display: "grid",
              gridTemplateColumns: `repeat(${GRID_SIZE}, ${CELL_PX}px)`,
              gridTemplateRows: `repeat(${GRID_SIZE}, ${CELL_PX}px)`,
              gap: `${GAP}px`, padding: `${BOARD_PAD}px`,
              background: GS.gridBg,
              backdropFilter: GS.blur,
              WebkitBackdropFilter: GS.blur,
              borderRadius: "18px",
              border: `1px solid ${GS.gridBorder}`,
              boxShadow: `${GS.shadowDeep}, inset 0 0.5px 0 rgba(255,255,255,0.08)`,
              position: "relative",
            }}>
              {Array.from({ length: GRID_SIZE }).map((_, row) =>
                Array.from({ length: GRID_SIZE }).map((_, col) => {
                  const cell = grid[row][col];
                  const isSel = isSelectedCell(row, col);
                  const bg = cellColor(row, col);
                  const isGhost = gc.some((c) => c.row === row && c.col === col);
                  const hasBlock = cell && !cell.isObstacle;
                  const isObs = cell && cell.isObstacle;
                  const dividers = cellDividers(row, col);
                  const radius = (hasBlock || isObs) ? cellRadius(row, col) : "8px";
                  const borders = cellBorders(row, col);
                  const borderColor = cell
                    ? "rgba(255,255,255,0.5)"
                    : "transparent";

                  return (
                    <div
                      key={`${row}-${col}`}
                      onMouseDown={(e) => {
                        if (mode === MODES.PLAY) handlePlayMouseDown(row, col, e);
                        if (mode === MODES.BUILD && cell) {
                          e.preventDefault();
                          const b = blocks.find((bl) => bl.id === cell.blockId);
                          if (b) {
                            setSelectedBlockId(b.id);
                            const startX = e.clientX;
                            const startY = e.clientY;
                            let dragStarted = false;

                            const onPendingMove = (ev) => {
                              const dx = ev.clientX - startX;
                              const dy = ev.clientY - startY;
                              if (!dragStarted && Math.sqrt(dx * dx + dy * dy) > 8) {
                                dragStarted = true;
                                window.removeEventListener("mousemove", onPendingMove);
                                window.removeEventListener("mouseup", onPendingUp);
                                setEditingBlockId(null);
                                setDraggingExisting({ ...b });
                                setDragGhost({ x: ev.clientX, y: ev.clientY });
                                setBlocks((prev) => prev.map((bl) =>
                                  bl.id === b.id ? { ...bl, row: -10, col: -10 } : bl
                                ));
                              }
                            };

                            const onPendingUp = () => {
                              window.removeEventListener("mousemove", onPendingMove);
                              window.removeEventListener("mouseup", onPendingUp);
                              if (!dragStarted) {
                                setEditingBlockId(b.id);
                                setEditLetters(b.letters.trimEnd());
                              }
                            };

                            window.addEventListener("mousemove", onPendingMove);
                            window.addEventListener("mouseup", onPendingUp);
                          }
                        }
                      }}
                      style={{
                        width: CELL_PX, height: CELL_PX,
                        background: isGhost && !cell
                          ? (gv ? "rgba(100,180,255,0.15)" : "rgba(255,100,80,0.15)")
                          : (!cell ? GS.emptyCell : "transparent"),
                        borderRadius: !cell ? "8px" : 0,
                        padding: 0,
                        position: "relative",
                        cursor: (mode === MODES.PLAY && hasBlock) || (mode === MODES.BUILD && (hasBlock || isObs)) ? "grab" : "default",
                        border: !cell ? `1px solid ${GS.emptyCellBorder}` : "none",
                        boxSizing: "border-box",
                        transition: "background 0.15s",
                        overflow: "visible",
                      }}
                    >
                      {(hasBlock || isObs) && (
                        <div style={{
                          position: "absolute",
                          inset: 0,
                          background: bg,
                          borderRadius: radius,
                          display: "flex", alignItems: "center", justifyContent: "center",
                          fontSize: "22px", fontWeight: 700,
                          fontFamily: "'Space Grotesk', sans-serif",
                          color: "rgba(255,255,255,0.95)",
                          textShadow: hasBlock ? "0 1px 4px rgba(0,0,0,0.5)" : "none",
                          letterSpacing: "2px",
                          borderStyle: "solid",
                          borderColor: borderColor,
                          borderTopWidth: borders ? borders.borderTop : 0,
                          borderRightWidth: borders ? borders.borderRight : 0,
                          borderBottomWidth: borders ? borders.borderBottom : 0,
                          borderLeftWidth: borders ? borders.borderLeft : 0,
                          boxShadow: isSel
                            ? `0 0 0 2px ${GS.selectedGlow}, 0 0 20px ${GS.selectedGlow}, inset 0 1px 0 rgba(255,255,255,0.25)`
                            : (hasBlock || isObs)
                            ? "inset 0 1px 0 rgba(255,255,255,0.3), inset 0 -1px 0 rgba(255,255,255,0.08), 0 0 8px rgba(255,255,255,0.07), 0 4px 12px rgba(0,0,0,0.3)"
                            : "none",
                          transition: "box-shadow 0.2s cubic-bezier(0.4,0,0.2,1)",
                          overflow: "visible",
                        }}>
                          <GlowingEffect
                            spread={30}
                            glow={true}
                            disabled={false}
                            proximity={48}
                            inactiveZone={0.01}
                            borderWidth={2}
                          />
                          {/* Glass reflection overlay */}
                          {hasBlock && (
                            <div style={{
                              position: "absolute", inset: 0, pointerEvents: "none",
                              background: `linear-gradient(${
                                135 + (mousePos.x - 0.5) * 40
                              }deg, rgba(255,255,255,0.18) 0%, rgba(255,255,255,0.04) 40%, transparent 60%, rgba(255,255,255,0.03) 100%)`,
                              borderRadius: "inherit",
                            }} />
                          )}
                          {/* Secondary refraction highlight */}
                          {hasBlock && (
                            <div style={{
                              position: "absolute",
                              top: 0, left: 0, right: 0, height: "45%",
                              pointerEvents: "none",
                              background: "linear-gradient(180deg, rgba(255,255,255,0.12) 0%, transparent 100%)",
                              borderRadius: "inherit",
                            }} />
                          )}
                          {/* Glass divider — left seam */}
                          {dividers.left && (
                            <div style={{
                              position: "absolute", top: "12%", bottom: "12%", left: 0, width: 1,
                              background: "linear-gradient(180deg, transparent 0%, rgba(255,255,255,0.2) 30%, rgba(255,255,255,0.25) 50%, rgba(255,255,255,0.2) 70%, transparent 100%)",
                              pointerEvents: "none",
                            }} />
                          )}
                          {/* Glass divider — top seam */}
                          {dividers.top && (
                            <div style={{
                              position: "absolute", left: "12%", right: "12%", top: 0, height: 1,
                              background: "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.2) 30%, rgba(255,255,255,0.25) 50%, rgba(255,255,255,0.2) 70%, transparent 100%)",
                              pointerEvents: "none",
                            }} />
                          )}
                          {/* Letter */}
                          <span style={{ position: "relative", zIndex: 1 }}>{cell.letter}</span>
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

          {/* BUILD side panel */}
          {mode === MODES.BUILD && (
            <div style={{
              width: 270,
              marginLeft: "40px",
              background: GS.glass,
              backdropFilter: GS.blur,
              WebkitBackdropFilter: GS.blur,
              borderRadius: GS.radius,
              padding: "20px",
              border: `1px solid ${GS.glassBorder}`,
              boxShadow: GS.shadowCard,
            }}>
              <h3 style={{
                margin: "0 0 14px", fontSize: "11px", fontWeight: 600,
                color: GS.accentWarm, letterSpacing: "3px", textTransform: "uppercase",
              }}>
                Drag Pieces onto Grid
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "18px" }}>
                {PIECE_TEMPLATES.map((tmpl, i) => {
                  const disabled = tmpl.isTarget && hasTarget;
                  return (
                    <div key={i} onMouseDown={(e) => onPaletteDragStart(tmpl, e)}
                      style={{
                        display: "flex", alignItems: "center", gap: "14px",
                        padding: "10px 14px", borderRadius: GS.radiusSm,
                        background: GS.glassInput,
                        border: `1px solid ${GS.inputBorder}`,
                        cursor: disabled ? "not-allowed" : "grab",
                        opacity: disabled ? 0.35 : 1,
                        transition: "all 0.2s cubic-bezier(0.4,0,0.2,1)",
                      }}
                      onMouseEnter={(e) => { if (!disabled) { e.currentTarget.style.background = GS.glassHover; e.currentTarget.style.borderColor = tmpl.accent; } }}
                      onMouseLeave={(e) => { e.currentTarget.style.background = GS.glassInput; e.currentTarget.style.borderColor = GS.inputBorder; }}
                    >
                      <PieceFigure tmpl={tmpl} />
                      <div>
                        <div style={{ fontSize: "13px", fontWeight: 600, color: disabled ? GS.textDim : GS.text }}>
                          {tmpl.isTarget ? "Target Block" : tmpl.isObstacle ? "Obstacle" : `${tmpl.orientation === "horizontal" ? "Horizontal" : "Vertical"} ${tmpl.length}`}
                        </div>
                        <div style={{ fontSize: "10px", color: GS.textDim, letterSpacing: "0.5px" }}>
                          {tmpl.isTarget ? "Red · Len 2 · Horiz" : tmpl.isObstacle ? "Black · 1×1 · Fixed" : `Blue · Len ${tmpl.length} · ${tmpl.orientation === "horizontal" ? "↔" : "↕"}`}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Letter editor */}
              {editingBlockId && blocks.find((b) => b.id === editingBlockId) && (
                <LetterEditor
                  block={blocks.find((b) => b.id === editingBlockId)}
                  editLetters={editLetters}
                  setEditLetters={setEditLetters}
                  saveLetters={saveLetters}
                  setBlocks={setBlocks}
                  editingBlockId={editingBlockId}
                  setEditingBlockId={setEditingBlockId}
                />
              )}

              {blocks.length > 0 && (
                <>
                  <div style={{ height: 1, background: GS.glassBorder, margin: "0 0 12px" }} />
                  <div style={{
                    fontSize: "10px", fontWeight: 600, color: GS.textDim, marginBottom: "8px",
                    letterSpacing: "2px", textTransform: "uppercase",
                  }}>Placed ({blocks.filter((b) => b.row >= 0 && b.col >= 0).length})</div>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", maxHeight: "200px", overflowY: "auto" }}>
                    {blocks.filter((b) => b.row >= 0 && b.col >= 0).map((b) => (
                      <div key={b.id}
                        onClick={() => {
                          setSelectedBlockId(b.id);
                          setEditingBlockId(b.id); setEditLetters(b.letters.trimEnd());
                        }}
                        style={{
                          display: "flex", justifyContent: "space-between", alignItems: "center",
                          padding: "6px 10px", borderRadius: "8px", fontSize: "12px", fontWeight: 500,
                          background: selectedBlockId === b.id ? GS.glassHover : "transparent",
                          border: selectedBlockId === b.id ? `1px solid ${GS.glassBorder}` : "1px solid transparent",
                          cursor: "pointer",
                          transition: "all 0.15s",
                        }}>
                        <span style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{
                            display: "inline-block", width: 12, height: 12, borderRadius: 4,
                            background: b.isObstacle ? GS.blockObs : b.isTarget ? GS.blockRed : GS.blockBlue,
                            border: `1px solid ${b.isObstacle ? "rgba(80,80,100,0.5)" : "rgba(255,255,255,0.15)"}`,
                            boxShadow: "0 1px 3px rgba(0,0,0,0.3)",
                          }} />
                          <span>{b.isObstacle ? (b.letters.trim() || "■") : b.letters.trim() || "—"}</span>
                          <span style={{ color: GS.textDim }}>({b.row},{b.col})</span>
                        </span>
                        <button onClick={(e) => { e.stopPropagation(); removeBlock(b.id); }}
                          style={{
                            background: "none", border: "none", color: GS.accentRed, cursor: "pointer",
                            fontSize: "14px", padding: "0 2px", lineHeight: 1, opacity: 0.7,
                            transition: "opacity 0.15s",
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.opacity = "1"}
                          onMouseLeave={(e) => e.currentTarget.style.opacity = "0.7"}
                        >✕</button>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {/* PLAY side panel */}
          {mode === MODES.PLAY && (
            <div style={{
              width: 210,
              background: GS.glass,
              backdropFilter: GS.blur,
              WebkitBackdropFilter: GS.blur,
              borderRadius: GS.radius,
              padding: "20px",
              border: `1px solid ${GS.glassBorder}`,
              boxShadow: GS.shadowCard,
            }}>
              <h3 style={{
                margin: "0 0 14px", fontSize: "11px", fontWeight: 600,
                color: GS.accentWarm, letterSpacing: "3px", textTransform: "uppercase",
              }}>How to Play</h3>
              <p style={{ fontSize: "12px", color: GS.textMuted, lineHeight: 1.7, margin: "0 0 12px" }}>
                Slide the <span style={{ color: GS.accentRed, fontWeight: 700 }}>red block</span> to the exit <span style={{ color: GS.accentRed }}>➜</span> on the right.
              </p>
              <p style={{ fontSize: "12px", color: GS.textMuted, lineHeight: 1.7, margin: "0 0 12px" }}>
                <strong style={{ color: GS.text }}>Drag</strong> blocks or <strong style={{ color: GS.text }}>click</strong> + <strong style={{ color: GS.text }}>arrow keys</strong>.
              </p>
              <p style={{ fontSize: "12px", color: GS.textMuted, lineHeight: 1.7, margin: 0 }}>
                Each drag = <span style={{ color: GS.accentWarm, fontWeight: 700 }}>1 move</span>, regardless of distance.
              </p>

              {selectedBlockId && (() => {
                const sb = blocks.find((b) => b.id === selectedBlockId);
                if (!sb || sb.isObstacle) return null;
                return (
                  <div style={{
                    marginTop: 16, padding: "12px", borderRadius: GS.radiusSm,
                    background: GS.glassInput, border: `1px solid ${GS.inputBorder}`,
                  }}>
                    <div style={{ fontSize: "10px", color: GS.textDim, marginBottom: "6px", letterSpacing: "2px", textTransform: "uppercase" }}>Selected</div>
                    <div style={{
                      fontSize: "20px", fontWeight: 700, letterSpacing: "4px",
                      color: sb.isTarget ? GS.accentRed : GS.accentBlue,
                      filter: `drop-shadow(0 0 8px ${sb.isTarget ? "rgba(255,107,107,0.4)" : "rgba(116,185,255,0.4)"})`,
                    }}>{sb.letters.trim() || "—"}</div>
                    <div style={{ fontSize: "11px", color: GS.textDim, marginTop: "4px" }}>
                      {sb.orientation === "horizontal" ? "↔ Horizontal" : "↕ Vertical"} · Len {sb.length}
                    </div>
                  </div>
                );
              })()}
            </div>
          )}
        </div>

        {/* Drag ghost */}
        {dragGhost && (draggingTemplate || draggingExisting) && (() => {
          const tmpl = draggingTemplate || {
            length: draggingExisting.isObstacle ? 1 : draggingExisting.length,
            orientation: draggingExisting.orientation,
            isTarget: draggingExisting.isTarget,
            isObstacle: draggingExisting.isObstacle,
            color: draggingExisting.isObstacle ? "rgba(20,20,40,0.9)" : draggingExisting.isTarget ? "rgba(220,50,47,0.85)" : "rgba(60,140,220,0.8)",
            accent: draggingExisting.isObstacle ? "rgba(80,80,100,0.5)" : draggingExisting.isTarget ? "rgba(255,90,80,0.7)" : "rgba(100,180,255,0.6)",
          };
          const isOutside = draggingExisting && !hoverCell;
          return (
            <div style={{
              position: "fixed", left: dragGhost.x + 14, top: dragGhost.y + 14,
              pointerEvents: "none", zIndex: 1000,
              opacity: isOutside ? 0.5 : 0.9,
              transition: "opacity 0.2s",
              filter: "drop-shadow(0 4px 12px rgba(0,0,0,0.5))",
            }}>
              <PieceFigure tmpl={tmpl} mini={36} />
              {isOutside && (
                <div style={{
                  marginTop: "8px", padding: "5px 12px", borderRadius: "8px",
                  background: "rgba(255,100,80,0.9)",
                  backdropFilter: "blur(8px)",
                  color: "#fff",
                  fontSize: "11px", fontWeight: 600, textAlign: "center",
                  whiteSpace: "nowrap",
                  border: "1px solid rgba(255,150,130,0.4)",
                }}>
                  🗑 Drop to delete
                </div>
              )}
            </div>
          );
        })()}

        <p style={{ marginTop: "20px", fontSize: "10px", color: GS.textDim, letterSpacing: "2px" }}>
          Grid: {GRID_SIZE}×{GRID_SIZE}{hasTarget ? ` · Exit: Row ${exitRow}` : ""}
        </p>
      </div>

      {/* Keyframe animation */}
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');
        @keyframes pulseArrow {
          0%, 100% { transform: translateX(0); opacity: 0.8; }
          50% { transform: translateX(4px); opacity: 1; }
        }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,0.2); }
      `}</style>
      <Analytics />
    </div>
  );
}

/* ── Glassmorphic shared styles ── */
const glassInputStyle = {
  padding: "10px 14px",
  background: GS.glassInput,
  border: `1px solid ${GS.inputBorder}`,
  borderRadius: GS.radiusSm,
  color: GS.text,
  fontSize: "13px",
  fontFamily: "'Space Grotesk', sans-serif",
  fontWeight: 500,
  outline: "none",
  boxSizing: "border-box",
  userSelect: "text",
  WebkitUserSelect: "text",
  backdropFilter: "blur(12px)",
  WebkitBackdropFilter: "blur(12px)",
  transition: "border-color 0.2s",
};

const inputStyle = glassInputStyle;

function GlassBtn({ children, onClick, accent, danger, disabled, small }) {
  const base = {
    padding: small ? "6px 12px" : "9px 18px",
    fontSize: small ? "11px" : "13px",
    fontWeight: 600,
    fontFamily: "'Space Grotesk', sans-serif",
    letterSpacing: "0.5px",
    borderRadius: GS.radiusSm,
    border: accent
      ? `1px solid rgba(255,159,67,0.35)`
      : danger
      ? `1px solid rgba(255,107,107,0.35)`
      : `1px solid ${GS.glassBorder}`,
    background: accent
      ? "rgba(255,159,67,0.12)"
      : danger
      ? "rgba(255,107,107,0.1)"
      : GS.glass,
    backdropFilter: "blur(16px)",
    WebkitBackdropFilter: "blur(16px)",
    color: disabled
      ? GS.textDim
      : accent
      ? GS.accentWarm
      : danger
      ? GS.accentRed
      : GS.text,
    cursor: disabled ? "not-allowed" : "pointer",
    opacity: disabled ? 0.4 : 1,
    transition: "all 0.2s cubic-bezier(0.4,0,0.2,1)",
    boxShadow: "inset 0 0.5px 0 rgba(255,255,255,0.08)",
  };
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={base}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.background = accent
            ? "rgba(255,159,67,0.22)"
            : danger
            ? "rgba(255,107,107,0.2)"
            : GS.glassHover;
          e.currentTarget.style.boxShadow = accent
            ? "inset 0 0.5px 0 rgba(255,255,255,0.1), 0 0 16px rgba(255,159,67,0.15)"
            : danger
            ? "inset 0 0.5px 0 rgba(255,255,255,0.1), 0 0 16px rgba(255,107,107,0.15)"
            : "inset 0 0.5px 0 rgba(255,255,255,0.15), 0 0 16px rgba(255,255,255,0.05)";
        }
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = base.background;
        e.currentTarget.style.boxShadow = base.boxShadow;
      }}
    >{children}</button>
  );
}

function GlassPanel({ children }) {
  return (
    <div style={{
      width: 360,
      background: GS.glass,
      backdropFilter: GS.blur,
      WebkitBackdropFilter: GS.blur,
      borderRadius: GS.radius,
      padding: "18px",
      border: `1px solid ${GS.glassBorder}`,
      marginBottom: "16px",
      boxShadow: GS.shadowCard,
    }}>{children}</div>
  );
}

function LetterEditor({ block, editLetters, setEditLetters, saveLetters, setBlocks, editingBlockId, setEditingBlockId }) {
  const len = block.isObstacle ? 1 : block.length;
  const cellRefs = useRef([]);
  const [focusIdx, setFocusIdx] = useState(0);

  useEffect(() => {
    cellRefs.current = cellRefs.current.slice(0, len);
    // Focus first empty cell or first cell
    const firstEmpty = editLetters.length;
    const idx = Math.min(firstEmpty, len - 1);
    setFocusIdx(idx);
    setTimeout(() => cellRefs.current[idx]?.focus(), 30);
  }, [block.id]);

  // Live-update the block whenever letters change
  const applyLetters = (newLetters) => {
    setEditLetters(newLetters);
    const padded = newLetters.toUpperCase().padEnd(len, " ").slice(0, len);
    setBlocks((prev) =>
      prev.map((b) => b.id === editingBlockId ? { ...b, letters: padded } : b)
    );
  };

  const handleKeyDown = (idx, e) => {
    e.stopPropagation();
    if (e.key === "Backspace") {
      e.preventDefault();
      const arr = editLetters.padEnd(len, " ").split("");
      arr[idx] = " ";
      const newLetters = arr.join("");
      applyLetters(newLetters);
      if (idx > 0) {
        setFocusIdx(idx - 1);
        setTimeout(() => cellRefs.current[idx - 1]?.focus(), 10);
      }
    } else if (e.key === "ArrowLeft" && idx > 0) {
      e.preventDefault();
      setFocusIdx(idx - 1);
      cellRefs.current[idx - 1]?.focus();
    } else if (e.key === "ArrowRight" && idx < len - 1) {
      e.preventDefault();
      setFocusIdx(idx + 1);
      cellRefs.current[idx + 1]?.focus();
    } else if (e.key === "Enter") {
      e.preventDefault();
      setEditingBlockId(null);
    } else if (e.key === "Escape") {
      e.preventDefault();
      setEditingBlockId(null);
    } else if (e.key.length === 1) {
      e.preventDefault();
      const char = e.key.toUpperCase();
      const arr = editLetters.padEnd(len, " ").split("");
      arr[idx] = char;
      const newLetters = arr.join("");
      applyLetters(newLetters);
      // Auto-advance
      if (idx < len - 1) {
        setFocusIdx(idx + 1);
        setTimeout(() => cellRefs.current[idx + 1]?.focus(), 10);
      } else {
        // Last char filled — auto-close
        setTimeout(() => setEditingBlockId(null), 200);
      }
    }
  };

  const padded = editLetters.padEnd(len, " ");
  const typeLabel = block.isTarget ? "Target" : block.isObstacle ? "Obstacle" : "Block";

  return (
    <div style={{
      padding: "14px", borderRadius: GS.radiusSm,
      background: GS.glassInput,
      border: `1px solid ${GS.inputBorder}`,
      marginBottom: "14px",
    }}>
      <div style={{
        fontSize: "10px", fontWeight: 600, color: GS.textDim, marginBottom: "10px",
        letterSpacing: "2px", textTransform: "uppercase",
      }}>
        {typeLabel} at ({block.row},{block.col}) — type to fill
      </div>
      <div style={{ display: "flex", gap: "6px", justifyContent: "center" }}>
        {Array.from({ length: len }).map((_, i) => {
          const char = padded[i];
          const isFocused = i === focusIdx;
          return (
            <div
              key={i}
              ref={(el) => cellRefs.current[i] = el}
              tabIndex={0}
              onFocus={() => setFocusIdx(i)}
              onKeyDown={(e) => handleKeyDown(i, e)}
              onMouseDown={(e) => e.stopPropagation()}
              onClick={(e) => { e.stopPropagation(); cellRefs.current[i]?.focus(); }}
              style={{
                width: 44, height: 50,
                display: "flex", alignItems: "center", justifyContent: "center",
                fontSize: "22px", fontWeight: 700,
                fontFamily: "'Space Grotesk', sans-serif",
                color: char.trim() ? GS.text : GS.textDim,
                background: isFocused ? "rgba(255,159,67,0.12)" : "rgba(255,255,255,0.04)",
                border: isFocused ? `2px solid ${GS.accentWarm}` : `1px solid ${GS.inputBorder}`,
                borderRadius: "8px",
                outline: "none",
                cursor: "text",
                userSelect: "text",
                WebkitUserSelect: "text",
                transition: "all 0.15s",
                boxShadow: isFocused ? `0 0 12px rgba(255,159,67,0.25)` : "none",
              }}
            >
              {char.trim() ? char : ""}
            </div>
          );
        })}
      </div>
      <div style={{
        fontSize: "9px", color: GS.textDim, marginTop: "8px", textAlign: "center",
        letterSpacing: "1px",
      }}>
        Type letters · Space for blank · Enter to close
      </div>
    </div>
  );
}