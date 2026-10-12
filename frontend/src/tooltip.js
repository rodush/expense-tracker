import { tick } from 'svelte';

export let tooltipText = '';
export let tooltipRowIndex = null;
export let tooltipLeft = 0;
export let tooltipTop = 0;
export let descriptionTooltipElement;

export async function showDescriptionTooltip(index, description, x, y) {
  tooltipRowIndex = index;
  tooltipText = String(description ?? '');
  await tick();
  positionDescriptionTooltip(x, y);
}

export function positionDescriptionTooltip(x, y) {
  if (!descriptionTooltipElement) return;
  const margin = 8;
  const offset = 14;
  const bounds = descriptionTooltipElement.getBoundingClientRect();
  const left = x + offset + bounds.width > window.innerWidth - margin
    ? x - bounds.width - offset
    : x + offset;
  const top = y + offset + bounds.height > window.innerHeight - margin
    ? y - bounds.height - offset
    : y + offset;
  tooltipLeft = Math.max(margin, Math.min(left, window.innerWidth - bounds.width - margin));
  tooltipTop = Math.max(margin, Math.min(top, window.innerHeight - bounds.height - margin));
}

export function hideDescriptionTooltip(event, index) {
  if (event.currentTarget.contains(event.relatedTarget)) return;
  if (tooltipRowIndex === index) tooltipRowIndex = null;
}
