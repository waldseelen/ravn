import { createRouter, createWebHashHistory } from 'vue-router'
import Dashboard from './components/Dashboard.vue'
import Library from './components/Library.vue'
import Settings from './components/Settings.vue'

const routes = [
  { path: '/', component: Dashboard },
  { path: '/library', component: Library },
  { path: '/settings', component: Settings },
]

export const router = createRouter({
  history: createWebHashHistory(),
  routes,
})
