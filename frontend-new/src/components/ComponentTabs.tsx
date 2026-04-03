import { COMPONENTS, COMPONENT_LABELS, type ComponentType } from "../types/game";

export const ComponentTabs = ({
  selected,
  onSelect,
}: {
  selected: ComponentType;
  onSelect: (c: ComponentType) => void;
}) => (
  <div className="mb-4 grid grid-cols-2 gap-2 md:grid-cols-6">
    {COMPONENTS.map((component) => (
      <button
        key={component}
        type="button"
        onClick={() => onSelect(component)}
        className={`px-2 py-2 text-xs uppercase ${
          selected === component
            ? "bg-surface-highest text-primary"
            : "bg-surface-container text-on-surface-variant"
        }`}
      >
        {COMPONENT_LABELS[component]}
      </button>
    ))}
  </div>
);
