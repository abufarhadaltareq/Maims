<template>
  <!-- Dedicated legal page: the terms/privacy/licence content lives here now
       instead of taking up the whole bottom of the home page. Reached from the
       footer links (Terms & Conditions, Privacy, Licence). -->
  <div class="font-brand">
    <LegalSection />
  </div>
</template>

<script setup>
import LegalSection from '../components/LegalSection.vue'
</script>