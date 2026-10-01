<template>
  <section id="legal" class="bg-brand-primary text-white font-brand scroll-mt-24">
    <div class="max-w-7xl mx-auto px-6 py-16">
      <div class="max-w-3xl mb-10">
        <p class="text-[11px] uppercase tracking-[0.25em] text-white/50 font-bold mb-3">Legal</p>
        <h2 class="text-3xl md:text-4xl font-extrabold tracking-tight mb-3">Terms, Privacy &amp; Licence</h2>
        <p class="text-white/70 leading-relaxed">
          The rules that govern shopping on {{ config.domain }} — how orders, payments, returns and your data are handled,
          and what you may do with our content. Last updated {{ details.updated }}.
        </p>
      </div>

      <!-- Document tabs -->
      <div role="tablist" aria-label="Legal documents" class="flex flex-wrap gap-2 mb-8">
        <button
          v-for="doc in docs"
          :id="`tab-${doc.id}`"
          :key="doc.id"
          role="tab"
          type="button"
          :aria-selected="activeId === doc.id"
          :aria-controls="`panel-${doc.id}`"
          :tabindex="activeId === doc.id ? 0 : -1"
          @click="selectDoc(doc.id)"
          @keydown="onTabKeydown($event, doc.id)"
          class="px-5 py-2.5 rounded-full text-sm font-semibold transition-all duration-200 border"
          :class="activeId === doc.id
            ? 'bg-white text-brand-primary border-white'
            : 'bg-white/5 text-white/70 border-white/15 hover:bg-white/10 hover:text-white'"
        >
          {{ doc.tab }}
        </button>
      </div>

      <!-- Active document -->
      <div
        v-if="activeDoc"
        :id="`panel-${activeDoc.id}`"
        role="tabpanel"
        :aria-labelledby="`tab-${activeDoc.id}`"
        class="bg-white/[0.04] border border-white/10 rounded-3xl p-6 md:p-10"
      >
        <div class="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-6">
          <div class="max-w-3xl">
            <h3 class="text-2xl font-bold tracking-tight">{{ activeDoc.title }}</h3>
            <p class="text-white/70 mt-2 leading-relaxed">{{ activeDoc.intro }}</p>
          </div>
          <button
            type="button"
            class="shrink-0 self-start text-xs font-bold uppercase tracking-widest text-white/60 hover:text-white transition-colors"
            @click="toggleAll"
          >
            {{ allExpanded ? 'Collapse all' : 'Expand all' }}
          </button>
        </div>

        <div class="divide-y divide-white/10 border-t border-white/10">
          <div v-for="section in activeDoc.sections" :key="section.heading">
            <button
              type="button"
              class="w-full text-left flex items-start justify-between gap-6 py-5 group"
              :aria-expanded="isExpanded(section.heading)"
              @click="toggleSection(section.heading)"
            >
              <span class="font-bold text-base md:text-lg group-hover:text-brand-accent transition-colors">{{ section.heading }}</span>
              <svg
                class="w-5 h-5 shrink-0 mt-0.5 text-white/50 group-hover:text-white transition-transform duration-300"
                :class="isExpanded(section.heading) ? 'rotate-45' : ''"
                fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true"
              >
                <path stroke-linecap="round" stroke-width="2" d="M12 5v14M5 12h14"></path>
              </svg>
            </button>

            <div v-show="isExpanded(section.heading)" class="pb-6 -mt-2 space-y-3 max-w-3xl text-white/70 leading-relaxed">
              <p v-for="(paragraph, i) in section.body" :key="i">{{ paragraph }}</p>
              <ul v-if="section.bullets" class="space-y-2 list-disc pl-5 marker:text-white/30">
                <li v-for="(item, i) in section.bullets" :key="i">{{ item }}</li>
              </ul>
            </div>
          </div>
        </div>
      </div>

      <!-- Small print -->
      <div class="mt-8 grid gap-4 md:grid-cols-3">
        <p v-for="(note, key) in notes" :key="key" class="text-xs leading-relaxed text-white/50 bg-white/[0.03] border border-white/10 rounded-2xl p-4">
          {{ note }}
        </p>
      </div>
    </div>
  </section>
</template>

<script setup>
import { ref, computed } from 'vue'
import { LEGAL_DOCS, LEGAL_DETAILS, LEGAL_NOTICE } from '../content/legal'
import { BRAND_CONFIG } from '../brand.config'

const props = defineProps({
  /** Optional subset of documents to show, e.g. ['legal-terms']. Defaults to all. */
  only: { type: Array, default: null },
  /** Document opened first. Accepts a doc id or the matching URL hash. */
  initial: { type: String, default: '' },
})

const config = BRAND_CONFIG
const details = LEGAL_DETAILS
const notes = LEGAL_NOTICE
const docs = computed(() => (props.only ? LEGAL_DOCS.filter((d) => props.only.includes(d.id)) : LEGAL_DOCS))

const hashId = window.location.hash.replace('#', '')
const hashMatch = LEGAL_DOCS.find((d) => d.id === hashId)
const firstAvailable = docs.value[0]?.id || ''

const activeId = ref(hashMatch && docs.value.some((d) => d.id === hashMatch.id) ? hashMatch.id : props.initial || firstAvailable)
const activeDoc = computed(() => docs.value.find((d) => d.id === activeId.value) || docs.value[0])

// First section open on load, the rest collapsed until the reader opens them.
const expanded = ref(new Set(activeDoc.value ? [activeDoc.value.sections[0]?.heading] : []))

const isExpanded = (heading) => expanded.value.has(heading)

const toggleSection = (heading) => {
  const next = new Set(expanded.value)
  next.has(heading) ? next.delete(heading) : next.add(heading)
  expanded.value = next
}

const toggleAll = () => {
  const total = activeDoc.value?.sections.length || 0
  expanded.value = expanded.value.size >= total ? new Set() : new Set(activeDoc.value.sections.map((s) => s.heading))
}

const selectDoc = (id) => {
  if (activeId.value === id) return
  activeId.value = id
  expanded.value = new Set(activeDoc.value ? [activeDoc.value.sections[0]?.heading] : [])
  history.replaceState(null, '', `#${id}`)
}

const onTabKeydown = (event, id) => {
  const index = docs.value.findIndex((d) => d.id === id)
  let next = null
  if (event.key === 'ArrowRight') next = (index + 1) % docs.value.length
  if (event.key === 'ArrowLeft') next = (index - 1 + docs.value.length) % docs.value.length
  if (event.key === 'Home') next = 0
  if (event.key === 'End') next = docs.value.length - 1
  if (next === null) return
  event.preventDefault()
  selectDoc(docs.value[next].id)
  document.getElementById(`tab-${docs.value[next].id}`)?.focus()
}
</script>
