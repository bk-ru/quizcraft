function defaultClone(snapshot) {
  if (typeof structuredClone === "function") {
    return structuredClone(snapshot);
  }
  return JSON.parse(JSON.stringify(snapshot));
}

export function createUndoStack({ limit = 50, clone = defaultClone } = {}) {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new Error("Undo stack limit must be a positive integer.");
  }
  if (typeof clone !== "function") {
    throw new Error("Undo stack clone must be a function.");
  }

  const snapshots = [];

  return {
    push(snapshot) {
      snapshots.push(clone(snapshot));
      if (snapshots.length > limit) {
        snapshots.splice(0, snapshots.length - limit);
      }
    },
    pop() {
      const snapshot = snapshots.pop();
      return snapshot === undefined ? null : clone(snapshot);
    },
    clear() {
      snapshots.length = 0;
    },
    get canUndo() {
      return snapshots.length > 0;
    },
  };
}
