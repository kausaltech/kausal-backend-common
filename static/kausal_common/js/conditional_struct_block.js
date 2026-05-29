(function () {
  "use strict";

  const RULES = window.KAUSAL_CONDITIONAL_RULES || {};

  function getFingerprint(structBlock) {
    const paths = [];

    for (const el of structBlock.children) {
      if (el.dataset && el.dataset.contentpath)
        paths.push(el.dataset.contentpath);
    }

    return JSON.stringify(paths.sort());
  }

  function initBlock(structBlock) {
    console.log("initBlock", structBlock);
    if (structBlock.dataset.kausalConditionalInitialized) {
      return;
    }

    const rules = RULES[getFingerprint(structBlock)];

    if (!rules || !rules.length) {
      return;
    }

    structBlock.dataset.kausalConditionalInitialized = "1";

    for (const rule of rules) {
      const triggerContainer = structBlock.querySelector(
        `[data-contentpath="${rule.trigger}"]`,
      );

      if (!triggerContainer) {
        continue;
      }

      const select = triggerContainer.querySelector("select");

      if (!select) {
        continue;
      }

      const targetEl = rule.targetPath
        ? rule.targetPath.reduce(
            (el, part) =>
              el && el.querySelector(`[data-contentpath="${part}"]`),
            structBlock,
          )
        : structBlock.querySelector(`[data-contentpath="${rule.target}"]`);

      if (!targetEl) {
        continue;
      }

      const update = () => {
        targetEl.style.display = rule.showFor.includes(select.value)
          ? ""
          : "none";
      };

      update();

      select.addEventListener("change", update);
    }
  }

  function initAll(root) {
    root.querySelectorAll(".struct-block").forEach(initBlock);

    if (root.classList && root.classList.contains("struct-block")) {
      initBlock(root);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    initAll(document);

    new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            initAll(node);
          }
        }
      }
    }).observe(document.body, { childList: true, subtree: true });
  });
})();
