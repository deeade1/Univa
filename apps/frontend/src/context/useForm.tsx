// hooks/useForm.ts
import { useState, useCallback } from 'react';

export type UseFormReturn<T> = {
  values: T;
  onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  reset: () => void;
  setValues: React.Dispatch<React.SetStateAction<T>>;
};

export function useForm<T extends Record<string, any>>(
  callback: () => void,
  initialState: T
): UseFormReturn<T> {
  const [values, setValues] = useState<T>(initialState);

  const onChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      const { name, type, checked, files, value } = event.target as HTMLInputElement;

      setValues(prev => ({
        ...prev,
        [name]: type === 'checkbox'
          ? checked
          : type === 'file'
          ? files?.[0]
          : value,
      }));
    },
    []
  );

  const onSubmit = useCallback(
    (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      callback();
    },
    [callback]
  );

  const reset = useCallback(() => {
    setValues(initialState);
  }, [initialState]);

  return { values, onChange, onSubmit, reset, setValues };
}
