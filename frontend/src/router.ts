import { createRouter, createWebHashHistory } from 'vue-router'
import DownloadTab from './components/DownloadTab.vue'
import ConverterTab from './components/ConverterTab.vue'
import SubtitleTab from './components/SubtitleTab.vue'
import FiltersTab from './components/FiltersTab.vue'
import MixerTab from './components/MixerTab.vue'
import UtilitiesTab from './components/UtilitiesTab.vue'
import QueuePanel from './components/QueuePanel.vue'
import Library from './components/Library.vue'
import Settings from './components/Settings.vue'

const routes = [
  { path: '/', component: DownloadTab },
  { path: '/converter', component: ConverterTab },
  { path: '/subtitles', component: SubtitleTab },
  { path: '/filters', component: FiltersTab },
  { path: '/mixer', component: MixerTab },
  { path: '/utilities', component: UtilitiesTab },
  { path: '/queue', component: QueuePanel },
  { path: '/library', component: Library },
  { path: '/settings', component: Settings },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
