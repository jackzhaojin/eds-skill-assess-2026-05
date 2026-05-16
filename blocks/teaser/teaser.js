import { createOptimizedPicture } from '../../scripts/aem.js';

const VARIANTS = ['banner', 'cards-2', 'cards-3', 'cards-4'];

function isCtaParagraph(p) {
  const links = p.querySelectorAll('a');
  if (!links.length) return false;
  return [...p.childNodes].every((node) => {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent.trim() === '';
    return ['A', 'EM', 'STRONG', 'BR'].includes(node.tagName);
  });
}

function markEyebrow(textCell) {
  const first = textCell.firstElementChild;
  if (!first || first.tagName !== 'P') return;
  const em = first.querySelector('em');
  if (!em || first.children.length !== 1) return;
  first.classList.add('teaser-eyebrow');
  first.textContent = em.textContent;
}

function markCtas(textCell) {
  const cta = [...textCell.querySelectorAll('p')].reverse().find(isCtaParagraph);
  if (!cta) return;
  cta.classList.add('teaser-ctas');
  cta.querySelectorAll('a').forEach((a, i) => {
    a.classList.add('button', i === 0 ? 'primary' : 'secondary');
  });
}

export default function decorate(block) {
  const rows = [...block.children];
  let variant = VARIANTS.find((v) => block.classList.contains(v));
  if (!variant) {
    variant = rows.length === 1 ? 'banner' : 'cards-3';
    block.classList.add(variant);
  }

  const ul = document.createElement('ul');
  rows.forEach((row) => {
    const li = document.createElement('li');
    li.className = 'teaser-item';

    [...row.children].forEach((cell) => {
      const wrap = document.createElement('div');
      if (cell.querySelector('picture')) {
        wrap.className = 'teaser-visual';
      } else {
        wrap.className = 'teaser-text';
        markEyebrow(cell);
        markCtas(cell);
      }
      wrap.append(...cell.childNodes);
      li.append(wrap);
    });

    ul.append(li);
  });

  ul.querySelectorAll('picture > img').forEach((img) => {
    const eager = variant === 'banner';
    img
      .closest('picture')
      .replaceWith(createOptimizedPicture(img.src, img.alt || '', eager, [{ width: '1200' }]));
  });

  block.replaceChildren(ul);
}
