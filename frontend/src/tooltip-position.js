export function calculateTooltipPosition(x, y, width, height, viewportWidth, viewportHeight) {
  const margin = 8;
  const offset = 14;
  const left = x + offset + width > viewportWidth - margin
    ? x - width - offset
    : x + offset;
  const top = y + offset + height > viewportHeight - margin
    ? y - height - offset
    : y + offset;

  return {
    left: Math.max(margin, Math.min(left, viewportWidth - width - margin)),
    top: Math.max(margin, Math.min(top, viewportHeight - height - margin)),
  };
}
