import { onScopeDispose, ref } from 'vue'

// Keep this breakpoint aligned with the compact shell in MainLayout.vue.
export function useCompactLayout() {
  const media = window.matchMedia('(max-width: 960px)')
  const isCompact = ref(media.matches)
  const update = () => { isCompact.value = media.matches }

  media.addEventListener('change', update)
  onScopeDispose(() => media.removeEventListener('change', update))

  return isCompact
}
