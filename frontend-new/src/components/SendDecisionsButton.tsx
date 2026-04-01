export const SendDecisionsButton = ({
  onClick,
  disabled,
}: {
  onClick: () => void;
  disabled?: boolean;
}) => (
  <button
    type="button"
    className="w-full bg-gradient-to-r from-primary to-primary-container px-4 py-3 text-sm font-semibold uppercase text-black disabled:opacity-50"
    onClick={onClick}
    disabled={disabled}
  >
    Send Decisions
  </button>
);
