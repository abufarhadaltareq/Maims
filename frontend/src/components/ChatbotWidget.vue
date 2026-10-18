<template>
  <div class="fixed bottom-6 right-6 z-[60] print:hidden">
    <!-- Closed: floating launcher -->
    <button
      v-if="!open"
      @click="toggleOpen"
      class="w-14 h-14 rounded-full bg-brand-accent text-white flex items-center justify-center shadow-2xl shadow-brand-accent/40 hover:scale-105 active:scale-95 transition transform text-2xl"
      aria-label="Open chat assistant"
      title="Chat with Maims AI assistant"
    >
      <span>💬</span>
    </button>

    <!-- Open: chat panel -->
    <div v-else class="w-full sm:w-[420px] h-[560px] sm:h-[700px] flex flex-col bg-white border border-gray-100 rounded-[1.5rem] shadow-2xl overflow-hidden ring-1 ring-gray-50/60">
      <!-- Header -->
      <div class="flex items-center justify-between px-5 py-4 bg-gradient-to-r from-brand-primary-600 to-brand-accent text-white rounded-b-[1rem] shadow-sm">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center text-brand-accent font-bold text-xl backdrop-blur">✨</div>
          <div>
            <div class="font-bold text-sm tracking-tight">{{ storeName }} Assistant</div>
            <div class="text-xs text-white/80">AI stylist &amp; order help</div>
          </div>
        </div>
        <button @click="toggleOpen" class="w-8 h-8 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center text-white transition" aria-label="Close chat">
          <span class="text-sm">✕</span>
        </button>
      </div>

      <!-- Messages -->
      <div class="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50" ref="messagesEl">
        <div v-if="messages.length === 0 && !loading" class="flex flex-col items-center justify-center h-full text-gray-400 text-sm">
          <span class="text-2xl mb-2">👋</span>
          Ask me about products, sizes, shipping, returns, or your order.
        </div>

        <!-- Greeting -->
        <div v-if="greeting && messages.length === 0 && !loading" class="flex gap-3">
          <div class="w-8 h-8 rounded-xl bg-brand-accent/10 flex items-center justify-center text-brand-accent text-lg shrink-0">🤖</div>
          <div class="bg-white border border-gray-100 rounded-2xl rounded-tl-none p-3 text-sm leading-relaxed text-gray-700 shadow-sm max-w-[85%]">
            {{ greeting }}
          </div>
        </div>

        <div
          v-for="(msg, i) in messages"
          :key="i"
          class="flex flex-col animate-in fade-in slide-in-from-sm duration-300"
        >
          <!-- User message -->
          <div v-if="msg.role === 'user'" class="flex justify-end">
            <div class="bg-brand-accent text-white rounded-2xl rounded-tr-none p-3 max-w-[85%] text-sm leading-relaxed shadow-sm">
              {{ msg.text }}
            </div>
          </div>

          <!-- Bot message -->
          <div v-else class="flex gap-3">
            <div class="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600 text-lg shrink-0">🤖</div>
            <div class="flex-1 bg-white border border-gray-100 rounded-2xl rounded-tr-none p-3 text-sm leading-relaxed text-gray-700 shadow-sm" v-html="renderText(msg.text)"></div>

            <!-- Products -->
            <div v-if="msg.products && msg.products.length" class="mt-3">
              <div class="flex gap-2 overflow-x-auto pb-1 no-scrollbar">
                <ChatProductCard
                  v-for="p in msg.products"
                  :key="`chat-${p.id}`"
                  :product="p"
                  class="shrink-0"
                />
              </div>
            </div>

            <!-- Action buttons -->
            <div v-if="msg.action" class="mt-3 flex gap-2">
              <button
                v-if="msg.action.type === 'whatsapp' && msg.action.url"
                @click="openExternal(msg.action.url)"
                class="flex items-center gap-2 bg-gradient-brand hover:brightness-95 text-white text-xs font-bold px-3 py-1.5 rounded-full transition"
              >
                <span class="text-xs">💬</span>
                Chat on WhatsApp
              </button>
            </div>
          </div>

          <!-- Suggestions -->
          <div v-if="msg.suggestions && msg.suggestions.length" class="mt-3 flex flex-wrap gap-2">
            <button
              v-for="(s, j) in msg.suggestions"
              :key="j"
              @click="sendQuick(s)"
              class="px-3 py-1.5 rounded-full border border-gray-200 bg-white text-xs text-gray-600 font-medium hover:bg-brand-accent hover:text-white hover:border-brand-accent transition"
            >
              {{ s }}
            </button>
          </div>
        </div>

        <!-- Loading -->
        <div v-if="loading" class="flex gap-3">
          <div class="w-8 h-8 rounded-xl bg-gray-100 flex items-center justify-center text-gray-600 text-lg shrink-0">🤖</div>
          <div class="flex flex-col gap-1.5 w-3/4">
            <div class="h-4 bg-gray-100 rounded w-3/4 animate-pulse"></div>
            <div class="h-4 bg-gray-100 rounded w-1/2 animate-pulse"></div>
          </div>
        </div>
      </div>

      <!-- Quick prompts (before first message) -->
      <div v-if="!loading && messages.length === 0 && suggestions.length" class="p-3 border-t border-gray-100 bg-white/80 backdrop-blur">
        <p class="text-[10px] font-bold uppercase tracking-wider text-gray-400 mb-2">Try asking</p>
        <div class="flex flex-wrap gap-1.5">
          <button
            v-for="(s, i) in suggestions.slice(0, 6)"
            :key="i"
            @click="sendQuick(s)"
            class="px-3 py-1.5 rounded-full border border-gray-100 bg-white text-xs text-gray-600 font-medium hover:bg-brand-accent hover:text-white hover:border-brand-accent transition shadow-sm"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <!-- Composer -->
      <div class="border-t border-gray-100 bg-white p-3">
        <div class="relative max-w-[400px] mx-auto">
          <input
            v-model="draft"
            @keydown.enter.exact="compose"
            placeholder="Type a message…"
            :disabled="loading"
            class="w-full pl-10 pr-10 py-3 bg-gray-50 border border-gray-200 rounded-full text-sm text-gray-800 outline-none focus:border-brand-accent focus:ring-2 focus:ring-brand-accent/20 transition placeholder:text-gray-400"
          />
          <span class="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400">💬</span>
          <button
            @click="compose"
            :disabled="loading || !draft.trim()"
            class="absolute right-2 top-1/2 -translate-y-1/2 bg-brand-accent text-white rounded-full p-1.5 hover:brightness-110 transition disabled:opacity-50 disabled:cursor-not-allowed"
            aria-label="Send"
          >
            <span class="text-xs">➤</span>
          </button>
        </div>
        <p v-if="error" class="mt-1 text-rose-500 text-[11px] font-medium">{{ error }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, nextTick, watch, onMounted } from 'vue'
import { storeToRefs } from 'pinia'
import { useChatbotStore } from '../stores/chatbot'
import ChatProductCard from './ChatProductCard.vue'

const store = useChatbotStore()
const draft = ref('')
const messagesEl = ref(null)

// storeToRefs keeps every piece of state reactive. Assigning directly
// (`const open = store.open`) snapshots the primitive value, so the panel
// would never toggle and async greeting/suggestions would never appear.
const { open, messages, suggestions, greeting, storeName, loading, error } = storeToRefs(store)

const toggleOpen = () => {
  store.setOpen(!store.open)
  nextTick(() => scrollBottom())
}

const compose = async () => {
  if (!draft.value.trim() || store.loading) return
  const text = draft.value.trim()
  draft.value = ''
  await store.send(text)
  nextTick(() => scrollBottom())
}

const sendQuick = (text) => {
  draft.value = text
  compose()
}

const scrollBottom = () => {
  if (messagesEl.value) {
    messagesEl.value.scrollTop = messagesEl.value.scrollHeight
  }
}

const openExternal = (url) => {
  window.open(url, '_blank', 'noopener,noreferrer')
}

const renderText = (text) => {
  if (!text) return ''
  return String(text)
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/\n/g, '<br>')
}

onMounted(() => {
  nextTick(() => scrollBottom())
})

watch([() => messages.value.length, () => loading.value], () => {
  nextTick(() => scrollBottom())
})
</script>

<style scoped>
.animate-in {
  animation: animateIn 0.25s ease-out both;
}
@keyframes animateIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
