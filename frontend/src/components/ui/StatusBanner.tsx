import { Link } from "react-router-dom";

type BannerType = "success" | "error" | "warning" | "info";

interface StatusBannerProps {
  type: BannerType;
  message: string;
  onDismiss?: () => void;
}

const styles: Record<BannerType, string> = {
  success: "bg-green-50 border-green-400 text-green-800",
  error: "bg-red-50 border-red-400 text-red-800",
  warning: "bg-yellow-50 border-yellow-400 text-yellow-800",
  info: "bg-blue-50 border-blue-400 text-blue-800",
};

function isAuthError(message: string) {
  return message.includes("401") || message.includes("403");
}

export function StatusBanner({ type, message, onDismiss }: StatusBannerProps) {
  const isAuth = type === "error" && isAuthError(message);

  return (
    <div
      className={`border rounded-lg p-4 flex items-start justify-between gap-3 ${styles[type]}`}
      role="alert"
    >
      <div className="flex-1 text-sm font-medium">
        {isAuth ? (
          <span>
            Session expired. Please{" "}
            <Link to="/login" className="underline font-semibold">
              log in again
            </Link>
            .
          </span>
        ) : (
          message
        )}
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="shrink-0 text-current opacity-60 hover:opacity-100 text-lg leading-none"
          aria-label="Dismiss"
        >
          &times;
        </button>
      )}
    </div>
  );
}
