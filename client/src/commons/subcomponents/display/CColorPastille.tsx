import { ColorRGB } from "../../../types/ColorRGB";

export interface CColorPastilleProps {
  color: ColorRGB;
  onClick?: () => void;
}

export function CColorPastille({ color, onClick }: CColorPastilleProps) {
  return (
    <div
      onClick={onClick}
      className="flex flex-col items-center bg-white w-12 h-12 border border-gray-300 rounded-full relative"
    >
      <div
        className="w-12 h-12 border border-gray-300 rounded-full transition-colors duration-500 ease-out"
        style={{ backgroundColor: `rgb(${color.red}, ${color.green}, ${color.blue})` }}
      />
    </div>
  );
}

export default CColorPastille;
