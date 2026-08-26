document.createTreeWalker(target, NodeFilter.SHOW_TEXT);
    let textNode = walker.nextNode();

    while (textNode) {
      if (textNode.textContent.trim()) textNodes.push(textNode);
      textNode = walker.nextNode();
    }
  });

  textNodes.forEach((textNode) => {
    const fragment = document.createDocumentFragment();

    textNode.textContent.split(/(\s+)/).forEach((part) => {
      if (!part || /^\s+$/.test(part)) {
        fragment.append(document.createTextNode(part));
        return;
      }

      const word = document.createElement("span");
      const activeWord = document.createElement("span");

      word.className = "buddy-fund__word";
      word.append(document.createTextNode(part));

      activeWord.className = "buddy-fund__word-active";
      activeWord.setAttribute("aria-hidden", "true");
      activeWord.textContent = part;
      word.append(activeWord);

      fragment.append(word);
    });

    textNode.replaceWith(fragment);
  });

  return [...copy.querySelectorAll(".buddy-fund__word")];
}

const fundHighlightStates = [...document.querySelectorAll("[data-fund-highlight]")]
  .map((copy) => {
    const words = buildFundHighlightWords(copy);

    return {
      beat: copy.closest(".buddy-fund__beat"),
      copy,
      overlays: words.map((word) => word.querySelector(".buddy-fund__word-active")),
      wordCount: words.length,
    };
  })
  .filter(({ beat, wordCount }) => beat && wordCount);

let fundHighlightFrame = 0;

function renderFundHighlights() {
  fundHighlightFrame = 0;

  const viewportHeight = window.innerHeight;
  const shouldAnimate = fundHighlightDesktop.matches && !reducedMotion.matches;
  const measuredStates = fundHighlightStates.map((state) => {
    const bounds = state.beat.getBoundingClientRect();
    const progressRange = Math.max(bounds.height + viewportHeight * 0.7, 1);
    const sectionProgress = clamp(
      (viewportHeight * 0.88 - bounds.top) / progressRange,
      0,
      1,
    );
    const readingProgress = shouldAnimate
      ? clamp((sectionProgress - 0.3) / 0.5, 0, 1) * state.wordCount
      : state.wordCount;

    return { readingProgress, state };
  });

  measuredStates.forEach(({ readingProgress, state }) => {
    state.overlays.forEach((overlay, index) => {
      const wordProgress = clamp(readingProgress - index, 0, 1);
      const clipPath = wordProgress >= 1
        ? "none"
        : `inset(0 ${((1 - wordProgress) * 100).toFixed(2)}% 0 0)`;

      overlay.style.clipPath = clipPath;
      overlay.style.webkitClipPath = clipPath;
    });
  });
}

function requestFundHighlightUpdate() {
  if (fundHighlightFrame || !fundHighlightStates.length) return;
  fundHighlightFrame = window.requestAnimationFrame(renderFundHighlights);
}

if (fundHighlightStates.length) {
  window.requestAnimationFrame(() => {
    renderFundHighlights();
    fundHighlightStates.forEach(({ copy }) => {
      copy.classList.add("is-fund-highlight-ready");
    });
  });

  window.addEventListener("scroll", requestFundHighlightUpdate, { passive: true });
  window.addEventListener("resize", requestFundHighlightUpdate);
  window.addEventListener("load", requestFundHighlightUpdate, { once: true });
  reducedMotion.addEventListener("change", requestFundHighlightUpdate);
  fundHighlightDesktop.addEventListener("change", requestFundHighlightUpdate);
  document.fonts?.ready.then(requestFundHighlightUpdate);
}

const faqItems = [...document.querySelectorAll("[data-faq-item]")];

function setFaqItemOpen(item, isOpen) {
  const question = item.querySelector(".faq-question");
  const answer = item.querySelector(".faq-answer-shell");

  item.dataset.open = String(isOpen);
  question?.setAttribute("aria-expanded", String(isOpen));
  answer?.setAttribute("aria-hidden", String(!isOpen));

  if (answer && "inert" in answer) {
    answer.inert = !isOpen;
  }
}

faqItems.forEach((item) => {
  const question = item.querySelector(".faq-question");

  setFaqItemOpen(item, item.dataset.open === "true");
  question?.addEventListener("click", () => {
    const shouldOpen = item.dataset.open !== "true";

    faqItems.forEach((faqItem) => {
      setFaqItemOpen(faqItem, faqItem === item && shouldOpen);
    });
  });
});
