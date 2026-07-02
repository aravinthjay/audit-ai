export const MAX_CASES_PER_INTAKE_RUN = 50;

export function rowsForCaseCreation<T>(rows: T[]) {
  return rows.slice(0, MAX_CASES_PER_INTAKE_RUN);
}

export function heldBackCaseCount(totalFlagged: number) {
  return Math.max(totalFlagged - MAX_CASES_PER_INTAKE_RUN, 0);
}
