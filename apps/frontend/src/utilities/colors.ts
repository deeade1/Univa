// apps/frontend/src/utilities/colors.ts
type HexColor = `#${string}`;
type RGBString = `${number}, ${number}, ${number}`;
type ColorShades = {
  [key: `${string}-shade-${number}`]: HexColor;
  [key: `${string}-tint-${number}`]: HexColor;
  [key: `${string}-rgb`]: RGBString;
  [key: string]: HexColor | RGBString;
};

/**
 * Ensure a string is a valid HexColor
 */
const ensureHexColor = (color: string): HexColor => {
  if (color.startsWith('#')) {
    if (/^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color)) {
      return color as HexColor;
    }
    throw new Error(`Invalid hex color format: ${color}`);
  }
  if (/^([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$/.test(color)) {
    return `#${color}` as HexColor;
  }
  throw new Error(`Invalid hex color format: ${color}`);
};

export const colorMix = (color1: string, color2: string, weight: number = 50): HexColor => {
  const hex1 = ensureHexColor(color1);
  const hex2 = ensureHexColor(color2);
  
  const d2h = (d: number) => d.toString(16).padStart(2, '0');
  const h2d = (h: string) => parseInt(h, 16);

  let mixedColor = '#';
  
  for (let i = 1; i <= 5; i += 2) {
    const v1 = h2d(hex1.substr(i, 2));
    const v2 = h2d(hex2.substr(i, 2));
    const mixedValue = Math.floor(v2 + (v1 - v2) * (weight / 100));
    mixedColor += d2h(mixedValue);
  }

  return mixedColor as HexColor;
};

export const tintColor = (color: string, weight: number = 50): HexColor => {
  const hexColor = ensureHexColor(color);
  const colorWithoutHash = hexColor.substr(1);
  return colorMix('#FFFFFF', colorWithoutHash, weight);
};

export const shadeColor = (color: string, weight: number = 50): HexColor => {
  const hexColor = ensureHexColor(color);
  const colorWithoutHash = hexColor.substr(1);
  return colorMix('#000000', colorWithoutHash, weight);
};

export const hexToRgb = (hex: string): RGBString => {
  const hexColor = ensureHexColor(hex).slice(1);
  const r = parseInt(hexColor.substring(0, 2), 16);
  const g = parseInt(hexColor.substring(2, 4), 16);
  const b = parseInt(hexColor.substring(4, 6), 16);
  return `${r}, ${g}, ${b}` as RGBString;
};

export const getColorShadeTint = (
  colorName: string,
  colorValue: string,
  darkMode: boolean = false
): ColorShades => {
  const hexColor = ensureHexColor(colorValue);
  const colors: ColorShades = {} as ColorShades;
  
  if (darkMode) {
    colors[`${colorName}-shade-80`] = tintColor(hexColor, 80);
    colors[`${colorName}-shade-60`] = tintColor(hexColor, 60);
    colors[`${colorName}-shade-40`] = tintColor(hexColor, 40);
    colors[`${colorName}-shade-20`] = tintColor(hexColor, 20);
    colors[`${colorName}-shade-10`] = tintColor(hexColor, 10);
    colors[`${colorName}-tint-10`] = shadeColor(hexColor, 10);
    colors[`${colorName}-tint-20`] = shadeColor(hexColor, 20);
    colors[`${colorName}-tint-40`] = shadeColor(hexColor, 40);
    colors[`${colorName}-tint-60`] = shadeColor(hexColor, 60);
    colors[`${colorName}-tint-80`] = shadeColor(hexColor, 80);
    colors[`${colorName}-tint-90`] = shadeColor(hexColor, 90);
  } else {
    colors[`${colorName}-shade-80`] = shadeColor(hexColor, 80);
    colors[`${colorName}-shade-60`] = shadeColor(hexColor, 60);
    colors[`${colorName}-shade-40`] = shadeColor(hexColor, 40);
    colors[`${colorName}-shade-20`] = shadeColor(hexColor, 20);
    colors[`${colorName}-shade-10`] = shadeColor(hexColor, 10);
    colors[`${colorName}-tint-10`] = tintColor(hexColor, 10);
    colors[`${colorName}-tint-20`] = tintColor(hexColor, 20);
    colors[`${colorName}-tint-40`] = tintColor(hexColor, 40);
    colors[`${colorName}-tint-60`] = tintColor(hexColor, 60);
    colors[`${colorName}-tint-80`] = tintColor(hexColor, 80);
    colors[`${colorName}-tint-90`] = tintColor(hexColor, 90);
  }

  colors[`${colorName}-rgb`] = hexToRgb(hexColor);
  colors[colorName] = hexColor;

  return colors;
};