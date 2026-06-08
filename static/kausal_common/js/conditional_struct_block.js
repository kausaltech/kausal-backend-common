class ConditionalStructBlockDefinition extends window.wagtailStreamField.blocks
  .StructBlockDefinition {
  render(placeholder, prefix, initialState, initialError) {
    const block = super.render(placeholder, prefix, initialState, initialError);
    const container = block.container[0];
    const StructBlockDef =
      window.wagtailStreamField.blocks.StructBlockDefinition;

    // Wagtail's StructBlock constructor uses
    //   `childDef instanceof this.blockDef.constructor`
    // to decide whether a child is a nested StructBlock (and thus already has
    // its own collapsible panel header, making an extra label redundant).
    // Because our constructor is ConditionalStructBlockDefinition rather than
    // StructBlockDefinition, plain StructBlock children fail this instanceof
    // check and get a spurious <label>. Remove it.
    for (const childDef of this.childBlockDefs) {
      if (childDef instanceof StructBlockDef) {
        const wrapper = container.querySelector(
          `:scope > [data-contentpath="${childDef.name}"]`,
        );
        if (wrapper) {
          const label = wrapper.querySelector(":scope > .w-field__label");
          if (label) label.remove();
        }
      }
    }

    const rules = this.meta.conditionalRules;

    if (!rules || !rules.length) {
      return block;
    }

    let hasRules = false;

    for (const rule of rules) {
      const targetEl = rule.targetPath.reduce(
        (el, part) =>
          el && el.querySelector(`[data-contentpath="${part}"]`),
        container,
      );
      if (!targetEl) continue;

      const wRules = {};
      for (const [trigger, values] of Object.entries(rule.triggers)) {
        wRules[`${prefix}-${trigger}`] = values;
      }
      targetEl.setAttribute("data-w-rules-target", "show");
      targetEl.setAttribute("data-w-rules", JSON.stringify(wRules));
      hasRules = true;
    }

    if (hasRules) {
      const existing = container.getAttribute("data-controller") || "";
      const controllers = existing ? `${existing} w-rules` : "w-rules";
      container.setAttribute("data-controller", controllers);

      const existingAction = container.getAttribute("data-action") || "";
      const action = existingAction
        ? `${existingAction} change->w-rules#resolve`
        : "change->w-rules#resolve";
      container.setAttribute("data-action", action);
    }

    return block;
  }
}

window.telepath.register(
  "kausal_common.blocks.ConditionalStructBlock",
  ConditionalStructBlockDefinition,
);
