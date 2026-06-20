import { useState } from "react";

export interface TierUpgradeState {
  isOpen: boolean;
  currentTier: string;
  requiredTier: string;
  feature: string;
}

export function useTierUpgrade() {
  const [state, setState] = useState<TierUpgradeState | null>(null);

  const handleResponse = async (response: Response): Promise<Response> => {
    if (response.status === 402) {
      try {
        const data = await response.clone().json();
        if (data.error === "tier_required") {
          setState({
            isOpen: true,
            currentTier: data.current_tier || "standard",
            requiredTier: data.required_tier || "enterprise",
            feature: data.message?.match(/'([^']+)'/)?.[1] || "this feature",
          });
        }
      } catch {
        // ignore parse errors
      }
    }
    return response;
  };

  const close = () => setState(null);

  return { upgradeState: state, handleResponse, closeUpgrade: close };
}
