import type { FundRealtimeData } from '@/api/fund'

export const deriveEstimateNav = (fund: FundRealtimeData, changePct: number): number | null => {
  const existingChange = Number(fund.estimate_change)
  const existingNav = Number(fund.estimate_nav)
  const previousNav = Number(fund.previous_nav)

  if (Number.isFinite(previousNav) && previousNav > 0) {
    return Number((previousNav * (1 + changePct / 100)).toFixed(4))
  }

  if (Number.isFinite(existingNav) && existingNav > 0 && Number.isFinite(existingChange)) {
    const baseNav = existingNav / (1 + existingChange / 100)
    if (Number.isFinite(baseNav) && baseNav > 0) {
      return Number((baseNav * (1 + changePct / 100)).toFixed(4))
    }
  }

  return Number.isFinite(existingNav) && existingNav > 0 ? existingNav : null
}
