<template>
  <Teleport to="body">
    <transition name="fade">
      <div v-if="modelValue" class="fixed inset-0 z-40 bg-ink-950/60 flex items-center justify-center p-4" @click.self="$emit('update:modelValue', false)">
        <div class="card w-full max-w-lg max-h-[90vh] overflow-y-auto">
          <div class="px-5 py-4 border-b border-ink-100 flex items-center justify-between">
            <h2 class="font-semibold text-ink-700">{{ title }}</h2>
            <button class="btn-ghost" @click="$emit('update:modelValue', false)" aria-label="Close">
              <svg viewBox="0 0 20 20" class="w-4 h-4" fill="currentColor"><path d="M4 4l12 12M4 16L16 4" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
            </button>
          </div>
          <div class="p-5">
            <slot />
          </div>
          <div v-if="$slots.footer" class="px-5 py-3 border-t border-ink-100 bg-ink-50 rounded-b-xl flex justify-end gap-2">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </transition>
  </Teleport>
</template>

<script setup lang="ts">
defineProps<{ modelValue: boolean; title: string }>();
defineEmits(['update:modelValue']);
</script>

<style scoped>
.fade-enter-active, .fade-leave-active { transition: opacity .15s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
