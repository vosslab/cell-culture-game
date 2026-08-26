// Restrictive, local-only SVG parser for the visual census.
//
// This parser builds only the tag/attribute tree needed by the census. It does
// not resolve XML entities, external resources, or stylesheet references.

function parseSvgTree(markup) {
  // The census accepts only local, well-formed markup and never resolves
  // entities or external resources (ASVS 1.5.1).
  if (/<!\s*(?:doctype|entity)\b/i.test(markup)) {
    throw new Error("asset census: SVG declarations and entities are not accepted");
  }
  const rootContainer = { tag: "#document", attributes: {}, children: [] };
  const stack = [rootContainer];
  let cursor = 0;
  while (cursor < markup.length) {
    const next = markup.indexOf("<", cursor);
    if (next === -1) break;
    if (markup.startsWith("<!--", next)) {
      const end = markup.indexOf("-->", next + 4);
      if (end === -1) throw new Error("asset census: unterminated SVG comment");
      cursor = end + 3;
      continue;
    }
    if (markup.startsWith("<?", next)) {
      const end = markup.indexOf("?>", next + 2);
      if (end === -1) throw new Error("asset census: unterminated SVG processing instruction");
      cursor = end + 2;
      continue;
    }
    if (markup.startsWith("<![CDATA[", next)) {
      const end = markup.indexOf("]]>", next + 9);
      if (end === -1) throw new Error("asset census: unterminated SVG CDATA");
      cursor = end + 3;
      continue;
    }
    const tagEnd = findTagEnd(markup, next + 1);
    const token = markup.slice(next + 1, tagEnd).trim();
    if (token.length === 0 || token.startsWith("!")) {
      throw new Error("asset census: invalid SVG declaration");
    }
    if (token.startsWith("/")) {
      const closingTag = token.slice(1).trim().toLowerCase();
      if (!/^[a-z][\w:.-]*$/i.test(closingTag) || stack.length === 1) {
        throw new Error("asset census: invalid SVG closing tag");
      }
      const open = stack.pop();
      if (open.tag !== closingTag) {
        throw new Error(`asset census: mismatched SVG closing tag '${closingTag}'`);
      }
    } else {
      const node = parseSvgOpenTag(token);
      stack.at(-1).children.push(node);
      if (!node.selfClosing) stack.push(node);
    }
    cursor = tagEnd + 1;
  }
  if (stack.length !== 1 || rootContainer.children.length !== 1) {
    throw new Error("asset census: SVG markup must contain one well-formed root");
  }
  const root = rootContainer.children[0];
  if (root.tag !== "svg") throw new Error("asset census: SVG markup has no <svg> root");
  return root;
}

function findTagEnd(markup, start) {
  let quote = null;
  for (let index = start; index < markup.length; index += 1) {
    const char = markup[index];
    if (quote !== null) {
      if (char === quote) quote = null;
    } else if (char === '"' || char === "'") {
      quote = char;
    } else if (char === ">") {
      return index;
    }
  }
  throw new Error("asset census: unterminated SVG tag");
}

function parseSvgOpenTag(token) {
  const selfClosing = /\/\s*$/.test(token);
  const body = (selfClosing ? token.slice(0, -1) : token).trim();
  const nameMatch = /^([a-z][\w:.-]*)(?:\s|$)/i.exec(body);
  if (nameMatch === null) throw new Error("asset census: invalid SVG opening tag");
  const tag = nameMatch[1].toLowerCase();
  const attributes = parseXmlAttributes(body.slice(nameMatch[0].length));
  return { tag, attributes, children: [], selfClosing };
}

function parseXmlAttributes(source) {
  const attributes = {};
  let cursor = 0;
  while (cursor < source.length) {
    while (/\s/.test(source[cursor] ?? "")) cursor += 1;
    if (cursor === source.length) break;
    const nameMatch = /^[a-z_:][\w:.-]*/i.exec(source.slice(cursor));
    if (nameMatch === null) throw new Error("asset census: malformed SVG attribute");
    const name = nameMatch[0].toLowerCase();
    cursor += name.length;
    while (/\s/.test(source[cursor] ?? "")) cursor += 1;
    if (source[cursor] !== "=") throw new Error("asset census: SVG attribute must have a value");
    cursor += 1;
    while (/\s/.test(source[cursor] ?? "")) cursor += 1;
    const quote = source[cursor];
    if (quote !== '"' && quote !== "'") {
      throw new Error("asset census: SVG attribute values must be quoted");
    }
    cursor += 1;
    const end = source.indexOf(quote, cursor);
    if (end === -1) throw new Error("asset census: unterminated SVG attribute value");
    if (Object.hasOwn(attributes, name)) {
      throw new Error(`asset census: duplicate SVG attribute '${name}'`);
    }
    attributes[name] = source.slice(cursor, end);
    cursor = end + 1;
  }
  return attributes;
}

export { parseSvgTree };
