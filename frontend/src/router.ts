import { createRouter, createWebHashHistory } from 'vue-router'
import Home from './components/Home.vue'
import DownloadTab from './components/DownloadTab.vue'
import StudioWorkspace from './components/StudioWorkspace.vue'
import Library from './components/Library.vue'
import Settings from './components/Settings.vue'

const routes = [
  { path: '/', component: Home },
  { path: '/download', component: DownloadTab },
  { path: '/studio', component: StudioWorkspace },
  { path: '/library', component: Library },
  { path: '/settings', component: Settings },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
