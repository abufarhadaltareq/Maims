<template>
  <aside class="filter-sidebar bg-white">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-sm font-extrabold uppercase tracking-[0.18em]">Filter</h3>
      <button v-if="hasActive" type="button" @click="$emit('clear')" class="text-xs font-bold text-[var(--color-content-secondary)] hover:text-[var(--color-content)] underline underline-offset-2">Clear all</button>
    </div>
    <div class="border-t border-gray-100 py-4">
      <button type="button" class="flex items-center gap-1.5 text-[13px] font-extrabold uppercase tracking-wider mb-3" @click="toggle('size')">
        <span class="text-[10px]">{{ open.size ? 'v' : '>' }}</span> Bust size
      </button>
      <div v-show="open.size" class="grid grid-cols-3 gap-2">
        <button v-for="s in sizes" :key="s.value" type="button" @click="$emit('toggle-size', s.value)" :class="isActive('sizes', s.value) ? 'border-[var(--color-brand)] bg-[var(--color-brand)] text-white' : 'border-gray-200 bg-white hover:border-[var(--color-brand)]'" class="border rounded px-2 py-2 text-[13px] font-semibold transition">{{ s.value }}</button>
        <p v-if="!sizes.length" class="col-span-3 text-xs text-gray-400">No sizes yet.</p>
      </div>
    </div>
    <div v-if="lengths.length" class="border-t border-gray-100 py-4">
      <button type="button" class="flex items-center gap-1.5 text-[13px] font-extrabold uppercase tracking-wider mb-3" @click="toggle('length')">
        <span class="text-[10px]">{{ open.length ? 'v' : '>' }}</span> Length
      </button>
      <div v-show="open.length" class="grid grid-cols-3 gap-2">
        <button v-for="l in lengths" :key="l.value" type="button" @click="$emit('toggle-length', l.value)" :class="isActive('lengths', l.value) ? 'border-[var(--color-brand)] bg-[var(--color-brand)] text-white' : 'border-gray-200 bg-white hover:border-[var(--color-brand)]'" class="border rounded px-2 py-2 text-[13px] font-semibold transition">{{ l.value }}</button>
      </div>
    </div>
    <div class="border-t border-gray-100 py-4">
      <button type="button" class="flex items-center gap-1.5 text-[13px] font-extrabold uppercase tracking-wider mb-3" @click="toggle('color')">
        <span class="text-[10px]">{{ open.color ? 'v' : '>' }}</span> Color
      </button>
      <div v-show="open.color" class="flex flex-wrap gap-2">
        <button v-for="c in colors" :key="c.value" type="button" @click="$emit('toggle-color', c.value)" :title="c.value" :style="{ backgroundColor: swatch(c.value) }" :class="isActive('colors', c.value) ? 'ring-2 ring-offset-2 ring-black scale-110' : 'ring-1 ring-black/15 hover:scale-110'" class="w-7 h-7 rounded-full transition-transform" />
        <p v-if="!colors.length" class="text-xs text-gray-400">No colors yet.</p>
      </div>
      <div v-if="activeColors.length" class="flex flex-wrap gap-1.5 mt-3">
        <span v-for="c in activeColors" :key="c" class="text-[11px] font-bold bg-gray-100 rounded-full px-2.5 py-1">{{ c }}</span>
      </div>
    </div>
    <div v-if="fabrics.length" class="border-t border-gray-100 py-4">
      <button type="button" class="flex items-center gap-1.5 text-[13px] font-extrabold uppercase tracking-wider mb-3" @click="toggle('fabric')">
        <span class="text-[10px]">{{ open.fabric ? 'v' : '>' }}</span> Fabric
      </button>
      <ul v-show="open.fabric" class="space-y-1.5">
        <li v-for="f in fabrics" :key="f.value">
          <button type="button" @click="$emit('toggle-fabric', f.value)" class="w-full flex items-center justify-between text-[13px] py-1" :class="isActive('fabrics', f.value) ? 'font-bold text-[var(--color-content)]' : 'text-[var(--color-content-secondary)]'">
            <span class="capitalize">{{ f.value.replace(/_/g, ' ') }}</span>
            <span class="text-xs text-gray-400">({{ f.count }})</span>
          </button>
        </li>
      </ul>
    </div>
  </aside>
</template>
<script setup>
import { reactive } from 'vue'
const props = defineProps({ sizes: { type: Array, default: () => [] }, colors: { type: Array, default: () => [] }, lengths: { type: Array, default: () => [] }, fabrics: { type: Array, default: () => [] }, selected: { type: Object, default: () => ({ sizes: [], colors: [], lengths: [], fabrics: [] }) }, hasActive: { type: Boolean, default: false }, activeColors: { type: Array, default: () => [] } })
defineEmits(['toggle-size', 'toggle-color', 'toggle-length', 'toggle-fabric', 'clear'])
const open = reactive({ size: true, color: true, length: true, fabric: true })
const toggle = (k) => { open[k] = !open[k] }
const norm = (v) => String(v || '').toLowerCase()
const isActive = (key, value) => (props.selected[key] || []).map(norm).includes(norm(value))
const NAMED = { red: '#e11d48', maroon: '#7A1F1F', pink: '#f9a8d4', black: '#111111', white: '#ffffff', ivory: '#fffff0', beige: '#f5f5dc', cream: '#fffdd0', green: '#16a34a', emerald: '#059669', olive: '#808000', mint: '#a7f3d0', blue: '#2563eb', navy: '#1e3a8a', sky: '#87ceeb', teal: '#0d9488', yellow: '#facc15', gold: '#d4af37', mustard: '#e1ad01', orange: '#f97316', purple: '#9333ea', lavender: '#e6e6fa', magenta: '#ff00ff', burgundy: '#800020', brown: '#92400e', grey: '#808080', gray: '#808080', silver: '#c0c0c0' }
const swatch = (name) => { const v = String(name || '').trim(); if (/^#([0-9a-f]{3}|[0-9a-f]{6})$/i.test(v)) return v; return NAMED[v.toLowerCase()] || '#d1d5db' }
</script>
