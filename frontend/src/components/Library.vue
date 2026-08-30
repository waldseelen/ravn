<template>
  <div class="max-w-6xl mx-auto space-y-6">
    <!-- Top Workspace Header -->
    <div
      class="flex flex-col sm:flex-row sm:items-center justify-between p-5 rounded-2xl border shadow-xl gap-4"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <div class="flex items-center gap-3">
        <div
          class="w-12 h-12 rounded-xl flex items-center justify-center text-2xl font-bold border"
          style="background-color: var(--bg-card); color: var(--accent-brass); border-color: var(--border-brass);"
        >
          <span>▦</span>
        </div>
        <div>
          <h1 class="text-base font-bold uppercase tracking-wider" style="color: var(--text-primary);">
            {{ t.workspaceTitle }}
          </h1>
          <p class="text-xs" style="color: var(--text-muted);">{{ t.workspaceSubtitle }}</p>
        </div>
      </div>

      <!-- Segmented Tab Switcher -->
      <div
        class="p-1 rounded-xl border flex items-center gap-1 self-start sm:self-auto"
        style="background-color: var(--bg-card); border-color: var(--border-subtle);"
      >
        <button
          @click="activeTab = 'library'"
          class="px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 cursor-pointer"
          :style="{
            backgroundColor: activeTab === 'library' ? 'var(--accent-brass)' : 'transparent',
            color: activeTab === 'library' ? 'var(--bg-primary)' : 'var(--text-secondary)'
          }"
        >
          <span>▦</span> {{ t.tabLibrary }}
        </button>
        <button
          @click="activeTab = 'history'"
          class="px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 cursor-pointer"
          :style="{
            backgroundColor: activeTab === 'history' ? 'var(--accent-brass)' : 'transparent',
            color: activeTab === 'history' ? 'var(--bg-primary)' : 'var(--text-secondary)'
          }"
        >
          <span>📜</span> {{ t.tabHistory }}
        </button>
      </div>
    </div>

    <!-- Collapsible Quick Guide -->
    <div
      class="rounded-2xl border overflow-hidden shadow-md transition"
      style="background-color: var(--bg-surface); border-color: var(--border-subtle);"
    >
      <button
        type="button"
        @click="guideExpanded = !guideExpanded"
        class="w-full p-4 flex items-center justify-between text-left transition hover:opacity-90 cursor-pointer"
        style="background-color: var(--bg-card);"
      >
        <div class="flex items-center gap-2">
          <span class="text-sm font-bold" style="color: var(--accent-brass);">💡</span>
          <span class="text-xs font-bold" style="color: var(--text-primary);">{{ t.guideTitle }}</span>
          <span class="text-[11px] hidden sm:inline" style="color: var(--text-muted);">— {{ t.guideSubtitle }}</span>
        </div>
        <span class="text-xs font-mono" style="color: var(--text-muted);">
          {{ guideExpanded ? '▲' : '▼' }}
        </span>
      </button>

      <div v-show="guideExpanded" class="p-4 space-y-2 text-xs border-t" style="border-color: var(--border-subtle); color: var(--text-secondary);">
        <p>• {{ t.guideLine1 }}</p>
        <p>• {{ t.guideLine2 }}</p>
        <p>• {{ t.guideLine3 }}</p>
      </div>
    </div>

    <!-- Workspace Active Subtab View -->
    <div>
      <LibraryTab v-if="activeTab === 'library'" />
      <HistoryTab v-else-if="activeTab === 'history'" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import LibraryTab from './LibraryTab.vue'
import HistoryTab from './HistoryTab.vue'

const activeTab = ref<'library' | 'history'>('library')
const guideExpanded = ref(false)

const t = {
  workspaceTitle: 'Medya Kütüphanesi ve Geçmiş',
  workspaceSubtitle: 'Yerel medya kataloglama, koleksiyon yönetimi ve indirme geçmişi',
  tabLibrary: 'Medya Kütüphanesi',
  tabHistory: 'İndirme Geçmişi',
  guideTitle: 'Kütüphane Kullanım Rehberi',
  guideSubtitle: 'Medya dosyalarınızı etiketleyin ve düzenleyin',
  guideLine1: 'İndirilen veya bilgisayarınızdaki medya dosyalarını kütüphaneye ekleyip arayabilirsiniz.',
  guideLine2: 'Koleksiyonlar oluşturarak dosyalarınızı tematik listelerde gruplayabilirsiniz.',
  guideLine3: 'Geçmiş sekmesinden tamamlanan indirmelerinizi inceleyebilir ve istatistiklerinizi görebilirsiniz.'
}
</script>
