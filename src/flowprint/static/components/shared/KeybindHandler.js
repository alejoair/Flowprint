import { useEffect } from "react";

export function KeybindHandler({ onSave, onNew }) {
  useEffect(() => {
    function handle(e) {
      const mod = e.ctrlKey || e.metaKey;
      if (mod && e.key === "s") { e.preventDefault(); onSave?.(); }
      if (mod && e.key === "n") { e.preventDefault(); onNew?.(); }
    }
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [onSave, onNew]);

  return null;
}
