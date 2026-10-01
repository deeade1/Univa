import { getElems } from './dom';

// Get style root variable
export const getRootVars = (property: string, elem: HTMLElement | string = document.body): string | null => {
  let target: Element = elem instanceof HTMLElement ? elem : getElemAsElement(elem);
  return getComputedStyle(target).getPropertyValue(property).trim() || null;
};

function getElemAsElement(selector: string): Element {
  const el = document.querySelector(selector);
  if (!el) throw new Error(`Element not found for selector: ${selector}`);
  return el;
}

// Add/update CSS root variables
export const setRootVariables = (variables: Record<string, string>): void => {
  const root = document.documentElement;
  for (const [key, value] of Object.entries(variables)) {
    root.style.setProperty(key, value);
  }
};

// Remove CSS root variables
export const removeRootVariables = (variables: Record<string, string>): void => {
  const root = document.documentElement;
  for (const key of Object.keys(variables)) {
    root.style.removeProperty(key);
  }
};

// Get color variables
export const getVariableColor = (): Record<string, string | null> => {
  const prefix = getRootVars("--prefix") || 'bs-';
  return {
    primary: getRootVars(`--${prefix}primary`),
    info: getRootVars(`--${prefix}info`),
    warning: getRootVars(`--${prefix}warning`),
    primary_light: getRootVars(`--${prefix}primary-tint-20`)
  };
};

// Set font family
export const setFontFamily = (type: string, fontFamily: string | null): void => {
  for (const el of Array.from(getElems(`[data-font-${type}="google"]`))) {
    el.remove();
  }

  if (fontFamily === null) {
    fontFamily = 'Inter';
  }

  if (fontFamily && fontFamily !== 'Inter') {
    const link = document.createElement('link');
    link.setAttribute('rel', 'stylesheet');
    link.setAttribute(`data-font-${type}`, 'google');
    link.setAttribute('href', `https://fonts.googleapis.com/css?family=${fontFamily}:300;400;500;700&display=swap`);
    document.head?.appendChild(link);
  }

  const prefix = getRootVars("--prefix") || 'bs-';
  setRootVariables({
    [`--${prefix}${type}-font-family`]: `${fontFamily}, sans-serif`
  });
};
