import type { MetricSlice } from './table';

type InstanceYearContext = {
  referenceYear?: number | null;
  minimumHistoricalYear: number;
};

/**
 * Prepare the year axis for chart rendering from a metric slice.
 *
 * Clips the visible range to the data available in the slice, handles the
 * reference-year gap, and returns filtered year arrays with their original
 * indices so callers can look up the matching values without re-slicing.
 *
 * @param slice - The metric slice to prepare years for
 * @param instance - Instance context providing referenceYear and minimumHistoricalYear
 * @param startYear - User-selected start of visible range
 * @param endYear - User-selected end of visible range
 */
export function getFilteredYears(
  slice: MetricSlice,
  instance: InstanceYearContext,
  startYear: number,
  endYear: number
) {
  const allYears = [...slice.historicalYears, ...slice.forecastYears];

  // Clip endYear to what the data actually covers
  const lastMetricYear = allYears[allYears.length - 1];
  const usableEndYear = lastMetricYear && endYear > lastMetricYear ? lastMetricYear : endYear;

  // Visible forecast range: intersection of forecast range and [startYear, usableEndYear]
  const forecastStart = slice.forecastYears[0];
  const forecastEnd = slice.forecastYears[slice.forecastYears.length - 1];
  const hasOverlap = forecastStart <= usableEndYear && startYear <= forecastEnd;
  const visibleForecastRange: [number, number] | null = hasOverlap
    ? [Math.max(forecastStart, startYear), Math.min(forecastEnd, usableEndYear)]
    : null;

  // Show the reference year only when it sits before minimumHistoricalYear (gap scenario)
  // and the user has scrolled back to it as their start year
  const showReferenceYear =
    !!instance.referenceYear &&
    startYear === instance.referenceYear &&
    instance.referenceYear !== instance.minimumHistoricalYear;
  const referenceYear = showReferenceYear ? instance.referenceYear : undefined;

  // Filter to [startYear, usableEndYear], excluding years before minimumHistoricalYear
  const filteredHistoricalYears = slice.historicalYears.filter(
    (year) => year >= startYear && year <= usableEndYear && year >= instance.minimumHistoricalYear
  );
  const filteredForecastYears = slice.forecastYears.filter(
    (year) => year >= startYear && year <= usableEndYear && year >= instance.minimumHistoricalYear
  );
  const filteredYears = [...filteredHistoricalYears, ...filteredForecastYears];

  if (referenceYear) {
    filteredYears.unshift(referenceYear);
  }

  // Indices into allYears so callers can extract the matching values
  const yearIndices = filteredYears.map((year) => allYears.indexOf(year));

  return { filteredYears, yearIndices, referenceYear, visibleForecastRange };
}
