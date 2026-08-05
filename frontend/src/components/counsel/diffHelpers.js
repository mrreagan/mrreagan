/**
 * Diff helpers shared between the counsel Diff modal and Rollback
 * Preview modal. Pure functions — no React, no side effects.
 */

// Auto-bump a semantic-version-lite string by its last dotted segment.
export function bumpMinor(v) {
  if (!v) return "1.0";
  const parts = String(v).split(".");
  const last = parts.pop();
  const n = parseInt(last, 10);
  if (Number.isNaN(n)) return `${v}.1`;
  parts.push(String(n + 1));
  return parts.join(".");
}

// Turn jsdiff parts into aligned side-by-side rows. Removed lines occupy
// the left column, added lines occupy the right column; common lines
// occupy both. Blank cells align surrounding context.
export function buildRows(parts) {
  const rows = [];
  let leftNum = 0;
  let rightNum = 0;
  for (const p of parts) {
    const lines = p.value.split("\n");
    if (lines.length && lines[lines.length - 1] === "") lines.pop();
    if (p.added) {
      for (const line of lines) {
        rightNum++;
        rows.push({
          left: null, leftNum: null, leftClass: "bg-white",
          right: line, rightNum, rightClass: "bg-[#EAF3EA] text-[#1E4030]",
        });
      }
    } else if (p.removed) {
      for (const line of lines) {
        leftNum++;
        rows.push({
          left: line, leftNum, leftClass: "bg-[#FBEBEB] text-[#7A2E2E]",
          right: null, rightNum: null, rightClass: "bg-white",
        });
      }
    } else {
      for (const line of lines) {
        leftNum++; rightNum++;
        rows.push({
          left: line, leftNum, leftClass: "bg-white",
          right: line, rightNum, rightClass: "bg-white",
        });
      }
    }
  }
  return rows;
}

// Count added/removed lines in a jsdiff parts array.
export function computeDiffStats(parts) {
  let added = 0;
  let removed = 0;
  for (const p of parts) {
    const lc = (p.value.match(/\n/g) || []).length || (p.value ? 1 : 0);
    if (p.added) added += lc;
    else if (p.removed) removed += lc;
  }
  return { added, removed };
}
