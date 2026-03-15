import { ref, watch, nextTick, type Ref } from 'vue'
import type { LogLine } from '@/types'

/**
 * Auto-scrolls a container to bottom when new log lines arrive.
 * Pauses when user scrolls up; resumes when scrolled back to bottom.
 */
export function useAutoScroll(
  logs: Ref<LogLine[]>,
  containerRef: Ref<HTMLElement | null>,
) {
  const isAutoScrolling = ref(true)

  function onScroll() {
    const el = containerRef.value
    if (!el) return
    // If user is within 50px of bottom, re-enable auto-scroll
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 50
    isAutoScrolling.value = atBottom
  }

  function scrollToBottom() {
    const el = containerRef.value
    if (!el) return
    el.scrollTop = el.scrollHeight
    isAutoScrolling.value = true
  }

  watch(
    () => logs.value.length,
    (_newLen, oldLen) => {
      if (!isAutoScrolling.value) return
      const isInitialLoad = (oldLen === 0 || oldLen === undefined) && _newLen > 0
      nextTick(() => {
        if (isInitialLoad) {
          requestAnimationFrame(() => scrollToBottom())
        } else {
          scrollToBottom()
        }
      })
    },
  )

  return { isAutoScrolling, onScroll, scrollToBottom }
}
