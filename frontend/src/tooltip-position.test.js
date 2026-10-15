import { describe, expect, it } from 'vitest';
import { calculateTooltipPosition } from './tooltip-position';

describe('calculateTooltipPosition', () => {
  it('keeps the tooltip inside the viewport near its bottom-right edge', () => {
    expect(calculateTooltipPosition(290, 190, 80, 50, 300, 200)).toEqual({
      left: 196,
      top: 126,
    });
  });
});
