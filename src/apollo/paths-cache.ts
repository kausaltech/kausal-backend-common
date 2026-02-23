import { makeVar } from '@apollo/client';

import type { InstanceGoalInput } from '../utils/paths/metric';

type PathsScenario = {
  id: string;
  name: string;
  isActive: boolean;
  isDefault: boolean;
};

// Extends InstanceGoalInput with fields added by PathsProvider augmentation
export type PathsGoal = InstanceGoalInput & {
  separateYears: number[] | null;
};

export const yearRangeVar = makeVar<[number, number]>(null!);
export const activeScenarioVar = makeVar<PathsScenario | null>(null);
export const activeGoalVar = makeVar<PathsGoal | null>(null);
export const showSettingsPanelVar = makeVar<boolean>(false);
