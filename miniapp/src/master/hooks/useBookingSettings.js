// miniapp/src/master/hooks/useBookingSettings.js
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getBookingSettings,
  updateBookingSettings,
  replaceWeeklySchedule,
  addScheduleException,
  removeScheduleException,
} from '../../api/client';

const KEY = ['booking-settings'];

/** GET /api/master/booking-settings — bundle: enabled/cutoff/horizon/weekly/exceptions. */
export function useBookingSettings() {
  return useQuery({ queryKey: KEY, queryFn: getBookingSettings });
}

/** Generic optimistic mutation factory — patches the bundle in cache,
 *  rolls back on error, re-fetches on settle. */
function useBundleMutation(mutationFn, patchFn) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn,
    onMutate: async (input) => {
      await qc.cancelQueries({ queryKey: KEY });
      const prev = qc.getQueryData(KEY);
      qc.setQueryData(KEY, (old) => patchFn(old, input));
      return { prev };
    },
    onError: (_err, _input, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEY, ctx.prev);
    },
    onSettled: () => qc.invalidateQueries({ queryKey: KEY }),
  });
}

export function useUpdateBookingSettings() {
  return useBundleMutation(updateBookingSettings, (old, next) => ({ ...old, ...next }));
}

export function useReplaceWeeklySchedule() {
  // Server returns {ok, count}; we still need to invalidate so weekly comes back fresh.
  // Optimistic patch: overwrite the weekly array in the bundle.
  return useBundleMutation(replaceWeeklySchedule, (old, intervals) => ({
    ...old,
    weekly: intervals.map((i, idx) => ({
      id: idx, weekday: i.weekday, start_time: i.start, end_time: i.end,
    })),
  }));
}

export function useAddScheduleException() {
  return useBundleMutation(addScheduleException, (old, body) => ({
    ...old,
    exceptions: [
      ...(old?.exceptions ?? []),
      { id: -1, ...body, start_time: body.start || null, end_time: body.end || null },
    ],
  }));
}

export function useRemoveScheduleException() {
  return useBundleMutation(removeScheduleException, (old, id) => ({
    ...old,
    exceptions: (old?.exceptions ?? []).filter(e => e.id !== id),
  }));
}
