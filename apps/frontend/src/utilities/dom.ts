// Get single element by selector
export const getElem = (selector: string): Element | null => {
  return document.querySelector(selector);
};

// Get all elements by selector
export const getElems = (selector: string): NodeListOf<Element> => {
  return document.querySelectorAll(selector);
};

// Add class(es) to element(s)
export const addClass = (elem: Element | string | NodeListOf<Element>, ...classNames: string[]): void => {
  let elements: Element[] = [];

  if (typeof elem === 'string') {
    elements = Array.from(getElems(elem));
  } else if (elem instanceof Element) {
    elements = [elem];
  } else {
    elements = Array.from(elem);
  }

  for (const el of elements) {
    for (const className of classNames) {
      el.classList.add(className);
    }
  }
};

// Remove class(es) from element(s)
export const removeClass = (elem: Element | string | NodeListOf<Element>, ...classNames: string[]): void => {
  let elements: Element[] = [];

  if (typeof elem === 'string') {
    elements = Array.from(getElems(elem));
  } else if (elem instanceof Element) {
    elements = [elem];
  } else {
    elements = Array.from(elem);
  }

  for (const el of elements) {
    for (const className of classNames) {
      el.classList.remove(className);
    }
  }
};

// Get attribute value
export const getAttr = (elem: Element, attr: string): string | null => {
  return elem.getAttribute(attr);
};

// Set attribute value
export const setAttr = (
  elems: Element | string | NodeListOf<Element>,
  object: { prop: string; value: string }
): void => {
  let elements: Element[] = [];

  if (typeof elems === 'string') {
    elements = Array.from(getElems(elems));
  } else if (elems instanceof Element) {
    elements = [elems];
  } else {
    elements = Array.from(elems);
  }

  for (const el of elements) {
    el.setAttribute(object.prop, object.value);
  }
};

// Remove attribute
export const removeAttr = (elem: Element, attr: string): void => {
  elem.removeAttribute(attr);
};

// Update inner HTML
export const setContent = (selector: string | NodeListOf<Element>, content: string): void => {
  let elements: Element[] = [];

  if (typeof selector === 'string') {
    elements = Array.from(getElems(selector));
  } else {
    elements = Array.from(selector);
  }

  for (const el of elements) {
    const leftJoin = el.getAttribute('data-leftJoin') || '';
    const rightJoin = el.getAttribute('data-rightJoin') || '';
    el.innerHTML = `${leftJoin}${content}${rightJoin}`;
  }
};

// Copy to clipboard
export const copyToClipboard = (value: unknown, isJson = false): void => {
  const textarea = document.createElement("textarea");
  document.body.appendChild(textarea);
  textarea.value = isJson ? JSON.stringify(value, null, 4) : String(value);
  textarea.select();
  document.execCommand('copy');
  textarea.remove();
};
