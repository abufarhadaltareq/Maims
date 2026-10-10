<template>
  <!-- Aarong-style top category nav: replaces left sidebar, sits under header -->
  <nav class="bg-white border-t border-gray-100 hidden md:block">
    <div class="max-w-[1600px] mx-auto px-4 sm:px-6">
      <ul v-if="!loading && !loadError" class="flex items-center justify-center gap-7 lg:gap-9 h-11">
        <li>
          <router-link
            to="/"
            exact-active-class="nav-active"
            class="nav-link"
          >
            All Products
          </router-link>
        </li>
        <li
          v-for="item in menuStructure"
          :key="item.slug || item.name"
          class="relative group h-full flex items-center"
        >
          <router-link
            v-if="item.slug"
            :to="`/category/${item.slug}`"
            active-class="nav-active"
            class="nav-link flex items-center gap-1"
          >
            {{ item.name.toUpperCase() }}
            <span v-if="item.subcategories?.length" class="text-[9px] text-gray-400 group-hover:text-black transition-colors">▼</span>
          </router-link>
          <span v-else class="nav-link cursor-default">{{ item.name.toUpperCase() }}</span>

          <!-- Hover dropdown for subcategories -->
          <div
            v-if="item.subcategories?.length"
            class="invisible opacity-0 group-hover:visible group-hover:opacity-100 transition-all duration-200 absolute left-1/2 -translate-x-1/2 top-full min-w-[200px] bg-white border border-gray-100 shadow-xl rounded-b-xl py-2 z-50"
          >
            <router-link
              v-for="sub in item.subcategories"
              :key="sub.slug"
              :to="`/category/${sub.slug}`"
              class="block px-5 py-2 text-[13px] font-medium text-gray-600 hover:text-black hover:bg-gray-50 capitalize whitespace-nowrap"
            >
              {{ sub.name }}
            </router-link>
          </div>
        </li>
      </ul>
      <div v-else-if="loading" class="flex items-center justify-center gap-6 h-11 text-[12px] text-gray-400 font-medium uppercase tracking-wider">
        <span>Loading collections…</span>
      </div>
      <ul v-else class="flex items-center justify-center gap-7 h-11">
        <li v-for="name in fallbackNames" :key="name">
          <span class="nav-link cursor-default">{{ name }}</span>
        </li>
      </ul>
    </div>
  </nav>

  <!-- Mobile: horizontal scroll row (no sidebar drawer) -->
  <nav class="bg-white border-t border-gray-100 md:hidden overflow-x-auto no-scrollbar">
    <div class="flex items-center gap-5 px-4 h-11 w-max min-w-full">
      <router-link to="/" exact-active-class="nav-active" class="nav-link whitespace-nowrap">All</router-link>
      <template v-if="menuStructure.length">
        <router-link
          v-for="item in menuStructure"
          :key="item.slug || item.name"
          :to="item.slug ? `/category/${item.slug}` : '/'"
          active-class="nav-active"
          class="nav-link whitespace-nowrap"
        >
          {{ item.name.toUpperCase() }}
        </router-link>
      </template>
      <template v-else>
        <span v-for="name in fallbackNames" :key="name" class="nav-link whitespace-nowrap">{{ name }}</span>
      </template>
    </div>
  </nav>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const backendCategories = ref([])
const loading = ref(true)
const loadError = ref(false)

const fallbackNames = ['WOMEN', 'MEN', 'KIDS', 'HOME DÉCOR', 'JEWELLERY']

const menuStructure = computed(() => {
  if (!backendCategories.value.length) return []
  return backendCategories.value.map((cat) => ({
    name: cat.name,
    slug: cat.slug,
    subcategories: (cat.children || []).map((c) => ({ name: c.name, slug: c.slug })),
  }))
})

const fetchCategories = async () => {
  loading.value = true
  loadError.value = false
  try {
    const res = await axios.get('/api/v1/categories/')
    backendCategories.value = Array.isArray(res.data) ? res.data : []
  } catch (e) {
    console.error('CategoryNav categories failed:', e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

onMounted(fetchCategories)
</script>

<style scoped>
.nav-link {
  font-size: 13px;
  font-weight: 500;
  letter-spacing: 0.04em;
  color: #111;
  text-transform: uppercase;
  white-space: nowrap;
  padding: 4px 0;
  border-bottom: 2px solid transparent;
  transition: border-color 0.2s, color 0.2s;
}
.nav-link:hover {
  border-bottom-color: #111;
}
.nav-active {
  border-bottom-color: #111;
  font-weight: 700;
}
.no-scrollbar::-webkit-scrollbar {
  display: none;
}
.no-scrollbar {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
