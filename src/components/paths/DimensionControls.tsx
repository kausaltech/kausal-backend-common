import type { Dispatch, SetStateAction } from 'react';

import { Grid } from '@mui/material';

import SelectDropdown from '@common/components/SelectDropdown';
import type { TFunction } from '@common/i18n';
import {
  type ParsedMetric,
  type SliceConfig,
  getOptionsForDimension,
  getSliceableDims,
  updateChoice,
} from '@common/utils/paths/metric';

type DimensionControlsProps = {
  parsedMetric: ParsedMetric;
  sliceConfig: SliceConfig;
  setSliceConfig: Dispatch<SetStateAction<SliceConfig>>;
  t: TFunction;
};

/**
 * Dimension and category filter controls for a dimensional metric chart.
 * Returns null when the metric has only one dimension and no groups
 * (i.e. there is nothing to slice by).
 */
export default function DimensionControls({
  parsedMetric,
  sliceConfig,
  setSliceConfig,
  t,
}: DimensionControlsProps) {
  const hasGroups = parsedMetric.dimensions.some((dim) => dim.groups.length);

  if (parsedMetric.dimensions.length <= 1 && !hasGroups) {
    return null;
  }

  const sliceableDims = getSliceableDims(parsedMetric, sliceConfig);

  return (
    <Grid container spacing={1} sx={{ marginBottom: 2 }}>
      {parsedMetric.dimensions.length > 1 && (
        <Grid size={{ md: 3 }} sx={{ display: 'flex' }} key="dimension">
          <SelectDropdown
            id="dimension"
            className="flex-grow-1"
            label={t('plot-choose-dimension')}
            onChange={(val) => {
              setSliceConfig((old) => ({
                ...old,
                dimensionId: val?.id || undefined,
              }));
            }}
            options={sliceableDims}
            value={sliceableDims.find((dim) => sliceConfig.dimensionId === dim.id) || null}
            isMulti={false}
            isClearable={false}
          />
        </Grid>
      )}

      {parsedMetric.dimensions.map((dim) => {
        const options = getOptionsForDimension(parsedMetric, dim.id, sliceConfig.categories);
        return (
          <Grid size={{ md: 4 }} sx={{ display: 'flex' }} key={dim.id}>
            <SelectDropdown
              id={`dim-${dim.id.replaceAll(':', '-')}`}
              className="flex-grow-1"
              helpText={dim.helpText ?? undefined}
              label={dim.label}
              options={options}
              value={options.filter((opt) => opt.selected)}
              isMulti={true}
              isClearable={true}
              onChange={(newValues) => {
                setSliceConfig((old) => updateChoice(parsedMetric, dim, old, newValues));
              }}
            />
          </Grid>
        );
      })}
    </Grid>
  );
}
