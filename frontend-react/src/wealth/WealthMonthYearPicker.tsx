import { currentYear, currentMonth, MONTHS } from "./constants";

export interface WealthMonthYearPickerProps {
  year: number;
  month: number;
  onYearChange: (year: number) => void;
  onMonthChange: (month: number) => void;
  minYear?: number;
  maxYear?: number;
}

export default function WealthMonthYearPicker({
  year,
  month,
  onYearChange,
  onMonthChange,
  minYear = 2020,
  maxYear = 2030,
}: WealthMonthYearPickerProps) {
  return (
    <div className="flex gap-4 items-center flex-wrap">
      <label className="flex items-center gap-2 text-sm text-text-secondary">
        Year
        <input
          type="number"
          className="input-field w-24"
          min={minYear}
          max={maxYear}
          value={year}
          onChange={(e) => onYearChange(Number(e.target.value))}
          aria-label="Year"
        />
      </label>
      <label className="flex items-center gap-2 text-sm text-text-secondary">
        Month
        <select
          className="input-field w-32"
          value={month}
          onChange={(e) => onMonthChange(Number(e.target.value))}
          aria-label="Month"
        >
          {MONTHS.map((m) => (
            <option key={m} value={m}>{m}</option>
          ))}
        </select>
      </label>
    </div>
  );
}

export { currentYear, currentMonth };
