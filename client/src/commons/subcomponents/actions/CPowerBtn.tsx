export interface CPowerBtnProps {
  power: boolean;
  onToggle: (power: boolean) => void;
  disabled?: boolean;
}

export function CPowerBtn(props: CPowerBtnProps) {
  return (
    <button
      disabled={props.disabled}
      aria-pressed={props.power}
      aria-label="power"
      className="w-14 h-14 rounded-full relative flex items-center justify-center dark:bg-gray-700 bg-gray-100 dark:border-gray-500 border-gray-200 border-2 disabled:opacity-50"
      onClick={() => props.onToggle(!props.power)}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
        strokeWidth={2.5}
        className={`w-8 h-8  ${props.power ? "stroke-green-500" : "stroke-red-500"} `}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M5.636 5.636a9 9 0 1 0 12.728 0M12 3v9"
        />
      </svg>
    </button>
  );
}
