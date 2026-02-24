import { useEffect, useRef } from 'react';

import {
  BarChart,
  type BarSeriesOption,
  CustomChart,
  LineChart,
  type LineSeriesOption,
  PieChart,
  type PieSeriesOption,
} from 'echarts/charts';
import {
  AriaComponent,
  DatasetComponent,
  type DatasetComponentOption,
  GraphicComponent,
  GridComponent,
  type GridComponentOption,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TitleComponent,
  type TitleComponentOption,
  TooltipComponent,
  type TooltipComponentOption,
  TransformComponent,
} from 'echarts/components';
import type { ComposeOption } from 'echarts/core';
import * as echarts from 'echarts/core';
import { LabelLayout, UniversalTransition } from 'echarts/features';
import { CanvasRenderer, SVGRenderer } from 'echarts/renderers';
import throttle from 'lodash-es/throttle';

import { useBaseTheme } from '@common/themes/mui-theme/use-base-theme';

import { getChartTheme } from './chart-theme';

echarts.use([
  BarChart,
  CustomChart,
  TitleComponent,
  TooltipComponent,
  GridComponent,
  DatasetComponent,
  TransformComponent,
  LegendComponent,
  LabelLayout,
  UniversalTransition,
  SVGRenderer,
  CanvasRenderer,
  GraphicComponent,
  LineChart,
  MarkLineComponent,
  MarkAreaComponent,
  PieChart,
  AriaComponent,
]);

// Hack to add margin on the chart to fit the legend
// Based on https://github.com/apache/echarts/issues/15654
// Assumes that the legend is at the bottom of the chart
const resizeLegend = (chart: echarts.ECharts) => {
  if (chart) {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access, @typescript-eslint/no-explicit-any
    const found = (chart as any)._componentsViews.find(
      // eslint-disable-next-line @typescript-eslint/no-explicit-any, @typescript-eslint/no-unsafe-member-access
      (entry: any) => entry.type === 'legend.plain'
    );
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
    const myLegendHeight: number = found?._backgroundEl?.shape?.height || 0;
    chart.setOption({
      grid: { bottom: myLegendHeight + 48 },
    });
  }
};

// Create an Option type with only the required components and charts via ComposeOption
export type ECOption = ComposeOption<
  | BarSeriesOption
  | LineSeriesOption
  | PieSeriesOption
  | TitleComponentOption
  | TooltipComponentOption
  | GridComponentOption
  | DatasetComponentOption
>;

const DEFAULT_STYLES: ECOption = {
  textStyle: {
    fontFamily: 'system-ui, sans-serif', // Force consistent font across platforms
  },
};

type Props = {
  isLoading: boolean;
  data?: echarts.EChartsCoreOption;
  height?: string;
  onZrClick?: (clickedDataIndex: [number, number]) => void;
  className?: string;
  // Resize the legend when the chart loaded or resized, also adds additional space to the bottom of the chart
  withResizeLegend?: boolean;
  renderer?: 'svg' | 'canvas';
};

export function Chart({
  isLoading,
  data,
  height = '400px',
  onZrClick,
  className,
  withResizeLegend = true,
  renderer = 'canvas',
}: Props) {
  const chartRef = useRef<echarts.ECharts | null>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);
  const theme = useBaseTheme();

  // Initialize the chart
  useEffect(() => {
    const chart = echarts.init(wrapperRef.current, getChartTheme(theme).theme, {
      renderer: renderer,
    });

    chartRef.current = chart;

    const throttledResize = throttle(
      () => {
        chart.resize();

        if (withResizeLegend) {
          resizeLegend(chart);
        }
      },
      1000,
      {
        leading: false,
        trailing: true,
      }
    );

    window.addEventListener('resize', throttledResize);

    return () => {
      throttledResize.flush();
      window.removeEventListener('resize', throttledResize);
      chart.clear();
      chart.dispose();
    };
  }, [theme, withResizeLegend, renderer]);

  // Show/hide the loading indicator
  useEffect(() => {
    if (chartRef.current) {
      if (isLoading) {
        chartRef.current.showLoading();
      } else {
        chartRef.current.hideLoading();
      }
    }
  }, [isLoading]);

  // Update the chart when the data changes
  useEffect(() => {
    if (chartRef.current && data) {
      const augmentedData = {
        ...data,
        ...DEFAULT_STYLES,
      };
      chartRef.current.setOption(augmentedData, true);

      if (withResizeLegend) {
        resizeLegend(chartRef.current);
      }
    }
  }, [data, withResizeLegend]);

  // Add click handler to the chart
  useEffect(() => {
    const chart = chartRef.current;
    const chartZr = chart?.getZr();
    const withClickHandler = typeof onZrClick === 'function';

    function handleClick(params: { offsetX: number; offsetY: number }) {
      if (chart && withClickHandler) {
        const pointInPixel = [params.offsetX, params.offsetY];
        const pointInGrid = chart.convertFromPixel('grid', pointInPixel);

        // Ensure we have a valid coordinate pair
        if (Array.isArray(pointInGrid) && pointInGrid.length >= 2) {
          const dataIndex: [number, number] = [pointInGrid[0], pointInGrid[1]];
          onZrClick(dataIndex);
        }
      }
    }

    if (chartZr && typeof onZrClick === 'function') {
      chartZr.on('click', handleClick);

      return () => {
        chartZr.off('click', handleClick);
      };
    }
  }, [onZrClick]);

  return <div ref={wrapperRef} className={className} style={{ height }} />;
}
