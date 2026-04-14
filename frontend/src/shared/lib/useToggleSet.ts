import { useCallback, useState } from 'react';

export function useToggleSet<T>(): readonly [Set<T>, (value: T) => void] {
  const [set, setSet] = useState<Set<T>>(() => new Set());
  const toggle = useCallback((value: T) => {
    setSet((prev) => {
      const next = new Set(prev);
      if (next.has(value)) next.delete(value);
      else next.add(value);
      return next;
    });
  }, []);
  return [set, toggle] as const;
}
