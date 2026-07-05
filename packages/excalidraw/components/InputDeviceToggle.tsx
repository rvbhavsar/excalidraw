import clsx from "clsx";

import "./InputDeviceToggle.scss";

import type { AppState } from "../types";

type InputDeviceMode = AppState["inputDeviceMode"];

const MODES: { value: InputDeviceMode; label: string; title: string }[] = [
  {
    value: "auto",
    label: "Auto",
    title: "Auto-detect mouse vs. trackpad per gesture",
  },
  {
    value: "mouse",
    label: "Mouse",
    title: "Mouse: wheel zooms, right-drag pans",
  },
  {
    value: "trackpad",
    label: "Trackpad",
    title: "Trackpad: two-finger scroll pans, pinch zooms",
  },
];

export const InputDeviceToggle = ({
  mode,
  onChange,
}: {
  mode: InputDeviceMode;
  onChange: (mode: InputDeviceMode) => void;
}) => {
  return (
    <div
      className="InputDeviceToggle"
      role="radiogroup"
      aria-label="Input device controls"
    >
      {MODES.map(({ value, label, title }) => (
        <button
          key={value}
          type="button"
          role="radio"
          aria-checked={mode === value}
          className={clsx({ active: mode === value })}
          title={title}
          onClick={() => onChange(value)}
        >
          {label}
        </button>
      ))}
    </div>
  );
};
