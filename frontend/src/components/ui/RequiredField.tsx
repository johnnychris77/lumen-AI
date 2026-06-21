export function RequiredLabel({ label }: { label: string }) {
  return (
    <label className="block text-sm font-medium text-gray-700">
      {label} <span className="text-red-500" aria-label="required">*</span>
    </label>
  );
}

export function FieldError({ message }: { message?: string }) {
  if (!message) return null;
  return (
    <p className="mt-1 text-sm text-red-600" role="alert">
      {message}
    </p>
  );
}
