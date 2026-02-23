import { useEffect, useMemo, useState } from 'react';

import { useReactiveVar } from '@apollo/client';
import { useTheme } from '@emotion/react';
import { Box } from '@mui/material';

import { activeGoalVar } from '@common/apollo/paths-cache';
import type { TFunction } from '@common/i18n';
import { genColorsFromTheme, setUniqueColors } from '@common/utils/paths/colors';
import {
  type MetricCategoryChoice,
  type MetricCategoryValues,
  type MetricSlice,
  type ParsedMetric,
  type SliceConfig,
  flatten,
  getDefaultSliceConfig,
  getFilteredYears,
  getGoalsForChoice,
  hasDimension,
  parseMetric,
  sliceBy,
} from '@common/utils/paths/metric';
import {
  getProgressTrackingScenario,
  metricHasProgressTrackingScenario,
} from '@common/utils/paths/progress-tracking';

import type { DimensionalNodeMetricFragment } from '@/common/__generated__/paths/graphql';

import DimensionControls from './DimensionControls';
import NodeGraph from './NodeGraph';
import ToolsMenu from './ToolsMenu';

type MetricDim = NonNullable<DimensionalNodeMetricFragment['metricDim']> & {
  measureDatapointYears?: number[] | null;
};

type BaselineForecast = { year: number; value: number };

type InstanceContext = {
  referenceYear?: number | null;
  minimumHistoricalYear: number;
  features?: {
    baselineVisibleInGraphs?: boolean | null;
    maximumFractionDigits?: number | null;
  } | null;
};

type SiteScenario = {
  id: string;
  kind: string;
  actualHistoricalYears?: number[] | null;
};

type SiteContext = {
  scenarios: SiteScenario[];
  baselineName?: string | null;
  minYear: number;
};

const overrideUnit = (
  cube: ParsedMetric,
  unit: { htmlShort: string; htmlLong?: string | null; short?: string | null },
  t: TFunction
) => {
  let longUnit = unit.htmlShort;
  // FIXME: Nasty hack to show 'CO2e' where it might be applicable until
  // the backend gets proper support for unit specifiers.
  // t∕(Einw.·a)
  if (hasDimension(cube, 'emission_scope') && !hasDimension(cube, 'greenhouse_gases')) {
    if (unit.short === 't/Einw./a') {
      longUnit = t.raw('tco2-e-inhabitant') as string;
    } else if (unit.short === 'kt/a') {
      longUnit = t.raw('ktco2-e') as string;
    }
  }
  return longUnit;
};

type DimensionalNodeVisualisationProps = {
  title: string | null | undefined;
  baselineForecast?: BaselineForecast[];
  metric: MetricDim;
  startYear: number;
  endYear: number;
  instance: InstanceContext;
  site?: SiteContext | null;
  withControls?: boolean;
  withTools?: boolean;
  color?: string | null;
  onClickMeasuredEmissions?: (year: number) => void;
  forecastTitle?: string;
  chartType?: 'bar' | 'line' | 'area';
  t: TFunction;
};

export default function DimensionalNodeVisualisation({
  title,
  metric,
  startYear,
  withControls = true,
  withTools = true,
  endYear,
  baselineForecast,
  color,
  onClickMeasuredEmissions,
  forecastTitle,
  chartType = 'bar',
  instance,
  site,
  t,
}: DimensionalNodeVisualisationProps) {
  const activeGoal = useReactiveVar(activeGoalVar);
  const theme = useTheme();
  const scenarios = site?.scenarios ?? [];
  const hasProgressTracking = metricHasProgressTrackingScenario(metric, scenarios);

  const parsedMetric = useMemo(() => parseMetric(metric), [metric]);

  // Slice config defines the dimension (dimensionId) and categories (categories[]) we are currently visualizing
  // Slice config is affected by the active goal and user selections
  const defaultConfig = getDefaultSliceConfig(parsedMetric, activeGoal);
  const [sliceConfig, setSliceConfig] = useState<SliceConfig>(defaultConfig);

  useEffect(() => {
    /**
     * If the active goal changes, we will reset the grouping + filtering
     * to be compatible with the new choices (if the new goal has common
     * dimensions with our metric).
     */
    if (!activeGoal) return;
    const newDefault = getDefaultSliceConfig(parsedMetric, activeGoal);
    setSliceConfig(newDefault);
  }, [activeGoal, parsedMetric]);

  const activeDimensionLabel = sliceConfig.dimensionId
    ? (parsedMetric.dimsById.get(sliceConfig.dimensionId)?.label ?? null)
    : null;

  // If we have category filters active, let's add them to the viz subtitle
  const activeCategoryLabels: { dimension: string; categories: string[] }[] = [];
  for (const [key, value] of Object.entries(sliceConfig.categories)) {
    if (value?.categories?.length && value.categories.length > 0) {
      activeCategoryLabels.push({
        dimension: parsedMetric.dimsById.get(key)?.label ?? '',
        categories: value.categories.map((catId) => {
          for (const dim of parsedMetric.dimensions) {
            const found = dim.categories.find((c) => c.id === catId);
            if (found) return found.label;
          }
          return '';
        }),
      });
    }
  }

  const subtitle = activeCategoryLabels
    .map((dim) => `${dim.dimension}: ${dim.categories.join(' & ')}`)
    .join(', ')
    .trim();

  const graphTitle = title
    ? `${title}` + (subtitle && activeDimensionLabel ? ` per ${activeDimensionLabel}` : '')
    : null;
  // Get the dimension that is currently sliced by
  const slicedDim = sliceConfig.dimensionId
    ? parsedMetric.dimsById.get(sliceConfig.dimensionId)
    : undefined;

  const slice: MetricSlice =
    (slicedDim ? sliceBy(parsedMetric, slicedDim.id, true, sliceConfig.categories) : null) ??
    flatten(parsedMetric, sliceConfig.categories);

  const goals = getGoalsForChoice(parsedMetric, sliceConfig.categories);
  const showBaseline =
    baselineForecast && site?.baselineName && instance.features?.baselineVisibleInGraphs;

  // Define current year setup
  const { filteredYears, yearIndices, referenceYear, visibleForecastRange } = getFilteredYears(
    slice,
    instance,
    startYear,
    endYear
  );

  const filteredProgressValues: number[] = [];
  const filteredProgressYears: number[] = [];

  // Create filtered data for progress tracking
  // Only show progress data for years where the metric has actual measured data
  const measureDatapointYears = metric.measureDatapointYears ?? [];
  const hasMeasuredYearsBeyondBaseline = measureDatapointYears.some(
    (year) => year !== instance.referenceYear && year !== site?.minYear
  );

  if (hasProgressTracking && slicedDim && hasMeasuredYearsBeyondBaseline) {
    const progressScenario = getProgressTrackingScenario(site!.scenarios);

    // Build category choice that filters to the progress tracking scenario dimension
    const scenarioDim = parsedMetric.dimensions.find((dim) =>
      dim.id.endsWith(':scenario:ScenarioName')
    );
    const progressCat = scenarioDim?.categories.find(
      (cat) => cat.originalId === progressScenario?.id
    );
    const progressChoice: MetricCategoryChoice =
      scenarioDim && progressCat
        ? {
            ...sliceConfig.categories,
            [scenarioDim.id]: { categories: [progressCat.id], groups: null },
          }
        : sliceConfig.categories;

    const progressSlice = sliceBy(parsedMetric, slicedDim.id, true, progressChoice);

    // Filter progress years to only include years where this specific metric has measured data
    const progressYears =
      progressScenario?.actualHistoricalYears?.filter(
        (year) =>
          year !== instance.referenceYear &&
          measureDatapointYears.includes(year) &&
          year !== site?.minYear
      ) ?? [];

    if (progressSlice?.totalValues && progressYears?.length) {
      const referenceYearIndex = slice.historicalYears.findIndex(
        (year) => year === instance.referenceYear
      );

      const historicalYears =
        referenceYearIndex !== -1
          ? progressSlice.historicalYears.slice(referenceYearIndex + 1)
          : progressSlice.historicalYears;

      const historicalValues =
        referenceYearIndex !== -1
          ? (progressSlice.totalValues.historicalValues.slice(referenceYearIndex + 1) ?? [])
          : (progressSlice.totalValues.historicalValues ?? []);

      const lastHist = slice.historicalYears.length - 1;
      const totalSumX = [site!.minYear, ...historicalYears, ...progressSlice.forecastYears];
      const totalSumY = [
        slice?.totalValues?.historicalValues?.[lastHist] ?? 0,
        ...historicalValues,
        ...progressSlice.totalValues.forecastValues,
      ];

      /**
       * Filter out data for years that are not in the progress scenario.
       * Include the reference year in order to draw a line from the total reference
       * year emissions to the first observed year emissions.
       */
      const { x: filteredX, y: filteredY } = totalSumX.reduce(
        (acc, x, index) =>
          [instance.referenceYear, ...progressYears].includes(x)
            ? { x: [...acc.x, x], y: [...acc.y, totalSumY[index]] }
            : acc,
        { x: [] as number[], y: [] as number[] }
      );

      filteredProgressYears.push(...filteredX);
      filteredProgressValues.push(...filteredY.filter((y) => y !== null));
    }
  }

  // Collect full data for each category in the chart
  const dataCategories: { name: string; values: (number | null)[]; color: string | null }[] =
    slice.categoryValues.map((cv: MetricCategoryValues) => ({
      name: cv.category.label,
      values: [...cv.historicalValues, ...cv.forecastValues],
      color: cv.color,
    }));

  // Create simple tables for category data, goal data, baseline data, progress data, and total data
  // Using the filtered years
  const headerRow = ['Category', ...filteredYears];
  const datasetTable = [
    headerRow,
    ...dataCategories.map((row) => [row.name, ...yearIndices.map((idx) => row.values[idx])]),
  ].filter((row) => row.length > 0);

  const goalTable =
    goals !== null
      ? [
          headerRow,
          [
            'Goal',
            ...filteredYears.map((year) => goals?.find((goal) => goal.year === year)?.value),
          ],
        ]
      : null;

  const baselineTable = showBaseline
    ? [
        headerRow,
        [
          'Baseline',
          ...filteredYears.map(
            (year) => baselineForecast?.find((forecast) => forecast.year === year)?.value
          ),
        ],
      ]
    : null;

  const progressTable =
    filteredProgressValues.length > 0 && filteredProgressYears.length > 0
      ? [
          headerRow,
          [
            'Progress',
            ...filteredYears.map(
              (year) => filteredProgressValues[filteredProgressYears.indexOf(year)] ?? null
            ),
          ],
        ]
      : null;

  const totalTable =
    slice.totalValues && metric.stackable
      ? [
          headerRow,
          [
            'Total',
            ...yearIndices.map(
              (idx) =>
                [...slice.totalValues!.historicalValues, ...slice.totalValues!.forecastValues][idx]
            ),
          ],
        ]
      : null;

  // Define colors for the categories
  const defaultColor = color || theme.graphColors.blue050;
  const categoryColors: string[] = [];
  const someCategoriesHaveColorSet = slice.categoryValues.some((cv) => cv.color);

  if (dataCategories.length > 1) {
    if (color || someCategoriesHaveColorSet) {
      // This mutates the slice.categoryValues array!!
      setUniqueColors(
        slice.categoryValues as MetricCategoryValues[],
        (cv) => cv.color,
        (cv, newColor) => {
          (cv as { color: string | null }).color = newColor;
        },
        defaultColor
      );
      categoryColors.push(...slice.categoryValues.map((cv) => cv.color ?? defaultColor));
    } else {
      categoryColors.push(...genColorsFromTheme(theme, dataCategories.length));
    }
  } else {
    categoryColors.push(defaultColor);
  }

  const hasNegativeValues = slice.categoryValues.some(
    (cv) =>
      cv.historicalValues.some((value) => Number(value) < 0) ||
      cv.forecastValues.some((value) => Number(value) < 0)
  );

  console.log('METRIC ', metric);
  return (
    <>
      {withControls && (
        <DimensionControls
          parsedMetric={parsedMetric}
          sliceConfig={sliceConfig}
          setSliceConfig={setSliceConfig}
          t={t}
        />
      )}
      <Box sx={{ position: 'relative' }}>
        <NodeGraph
          title={graphTitle}
          subtitle={subtitle}
          dataTable={datasetTable}
          goalTable={goalTable}
          baselineTable={baselineTable}
          progressTable={progressTable}
          totalTable={totalTable}
          unit={overrideUnit(parsedMetric, metric.unit, t)}
          referenceYear={referenceYear}
          forecastRange={visibleForecastRange}
          categoryColors={categoryColors}
          theme={theme}
          maximumFractionDigits={instance.features?.maximumFractionDigits ?? undefined}
          baselineLabel={site?.baselineName}
          showTotalLine={hasNegativeValues && metric.stackable && dataCategories.length > 1}
          onClickMeasuredEmissions={onClickMeasuredEmissions}
          forecastTitle={forecastTitle}
          stackable={metric.stackable}
          chartType={chartType}
        />
        {withTools && <ToolsMenu cube={parsedMetric} sliceConfig={sliceConfig} t={t} />}
      </Box>
    </>
  );
}
