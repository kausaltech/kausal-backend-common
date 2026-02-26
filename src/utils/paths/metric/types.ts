/**
 * Dimensional Metric Types
 *
 * This module defines standalone types for working with dimensional metrics from Paths.
 * Input types define the "contract" that GraphQL fragments must satisfy - each app's
 * codegen will produce types assignable to these.
 */

// === INPUT TYPES (expected shape from GraphQL) ===

/**
 * A single year/value data point from a node metric.
 */
export type NodeMetricValueInput = {
  readonly year: number;
  readonly value: number;
};

/**
 * Raw metric shape from a node's `metric` field (forecastValues / historicalValues).
 * This is the shape produced by GraphQL fragments on outcome nodes.
 */
export type NodeMetricInput = {
  readonly forecastValues: readonly NodeMetricValueInput[];
  readonly historicalValues: readonly NodeMetricValueInput[];
};

/**
 * A category within a metric dimension.
 */
export type MetricDimensionCategoryInput = {
  readonly id: string;
  readonly originalId: string | null;
  readonly label: string;
  readonly color: string | null;
  readonly order: number | null;
  readonly group: string | null;
};

/**
 * A category group within a metric dimension.
 */
export type MetricCategoryGroupInput = {
  readonly id: string;
  readonly originalId: string | null;
  readonly label: string;
  readonly color: string | null;
  readonly order: number | null;
};

/**
 * A dimension of a metric (e.g., sector, scope, energy carrier).
 */
export type MetricDimensionInput = {
  readonly id: string;
  readonly label: string;
  readonly originalId: string | null;
  readonly helpText: string | null;
  readonly categories: readonly MetricDimensionCategoryInput[];
  readonly groups: readonly MetricCategoryGroupInput[];
};

/**
 * A goal definition with target values.
 */
export type MetricGoalInput = {
  readonly categories: readonly string[];
  readonly groups: readonly string[];
  readonly values: readonly {
    readonly year: number;
    readonly value: number;
    readonly isInterpolated: boolean;
  }[];
};

/**
 * Unit information for a metric.
 */
export type MetricUnitInput = {
  readonly htmlShort: string;
  readonly short: string;
};

/**
 * Reference to a normalization metric.
 */
export type MetricNormalizedByInput = {
  readonly id: string;
  readonly name: string;
} | null;

/**
 * The expected shape of a DimensionalMetric from GraphQL.
 * Your GraphQL fragment must include at least these fields.
 */
export type MetricInput = {
  readonly id: string;
  readonly name: string;
  readonly dimensions: readonly MetricDimensionInput[];
  readonly goals: readonly MetricGoalInput[];
  readonly unit: MetricUnitInput;
  readonly stackable: boolean;
  readonly normalizedBy: MetricNormalizedByInput;
  readonly forecastFrom: number | null;
  readonly years: readonly number[];
  readonly values: readonly (number | null)[];
};

/**
 * The expected shape of a goal from instance context.
 * Used for goal-based filtering.
 */
export type InstanceGoalInput = {
  readonly id: string;
  readonly label: string | null;
  readonly default: boolean;
  readonly disabled: boolean;
  readonly outcomeNode: { readonly id: string } | null;
  readonly dimensions: readonly {
    readonly dimension: string;
    readonly categories: readonly string[];
    readonly groups: readonly string[] | null;
  }[];
};

// === PROCESSED/INTERNAL TYPES ===

/**
 * Category from a dimension (same as input).
 */
export type MetricDimensionCategory = MetricDimensionCategoryInput;

/**
 * Enhanced category group with resolved categories.
 */
export type MetricCategoryGroup = MetricCategoryGroupInput & {
  readonly categories: readonly MetricDimensionCategory[];
};

/**
 * Enhanced dimension with groups resolved.
 */
export type MetricDimension = Omit<MetricDimensionInput, 'groups'> & {
  readonly groupsById: ReadonlyMap<string, MetricCategoryGroup>;
  readonly groups: readonly MetricCategoryGroup[];
};

/**
 * Dimension categories for a single row.
 */
export type DimCats = {
  readonly [dimId: string]: MetricDimensionCategory;
};

/**
 * A single data row with dimension category assignments.
 */
export type MetricRow = {
  readonly year: number;
  readonly value: number | null;
  readonly dimCats: DimCats;
};

/**
 * The parsed/processed metric data structure.
 */
export type ParsedMetric = {
  readonly id: string;
  readonly name: string;
  readonly unit: { readonly htmlShort: string; readonly short: string };
  readonly stackable: boolean;
  readonly forecastFrom: number | null;
  readonly years: readonly number[];
  readonly values: readonly (number | null)[];
  readonly dimensions: readonly MetricDimension[];
  readonly dimsById: ReadonlyMap<string, MetricDimension>;
  readonly rows: readonly MetricRow[];
  readonly goals: MetricInput['goals'];
  readonly normalizedBy: MetricInput['normalizedBy'];
};

/**
 * Category filter choice for a single dimension.
 */
export type CatDimChoice = {
  readonly groups: readonly string[] | null;
  readonly categories: readonly string[];
};

/**
 * Filter choices across all dimensions.
 */
export type MetricCategoryChoice = {
  readonly [dimId: string]: CatDimChoice | undefined;
};

/**
 * Configuration for slicing/grouping data.
 */
export type SliceConfig = {
  readonly dimensionId: string | undefined;
  readonly categories: MetricCategoryChoice;
};

/**
 * Category representation for output.
 */
export type MetricCategory = Partial<MetricDimensionCategory | MetricCategoryGroup> &
  Pick<MetricDimensionCategory, 'id' | 'label' | 'color' | 'order'>;

/**
 * Values for a category in a slice.
 */
export type MetricCategoryValues = {
  readonly category: MetricCategory;
  readonly forecastValues: readonly (number | null)[];
  readonly historicalValues: readonly (number | null)[];
  readonly isNegative: boolean;
  readonly color: string | null;
};

/**
 * Data structure for a metric slice.
 */
export type MetricSliceData = {
  readonly historicalYears: readonly number[];
  readonly forecastYears: readonly number[];
  readonly categoryValues: readonly MetricCategoryValues[];
  readonly totalValues: MetricCategoryValues | null;
  readonly dimensionLabel: string;
  readonly unit: string;
};

/**
 * Single year data result.
 */
export type SingleYearData = {
  readonly categoryTypes: readonly {
    readonly id: string;
    readonly type: 'group' | 'category';
    readonly options: readonly string[];
  }[];
  readonly allLabels: readonly {
    readonly id: string;
    readonly label: string;
    readonly color: string | null;
  }[];
  readonly rows: readonly (readonly (number | null)[])[];
};

/**
 * Table data result.
 */
export type TableData = {
  readonly header: readonly { readonly key: string; readonly label: string }[];
  readonly rows: readonly { readonly [key: string]: string | number | null }[];
  readonly hasTotals: boolean;
  readonly forecastFromColumn: number;
};

/**
 * Labels for table creation.
 */
export type TableLabels = {
  readonly total?: string;
  readonly type?: string;
  readonly year?: string;
  readonly unit?: string;
  readonly historical?: string;
  readonly forecast?: string;
};

/**
 * Export options.
 */
export type ExportOptions = {
  readonly years?: readonly number[];
  readonly tableTitle?: string;
  readonly labels?: TableLabels;
};
