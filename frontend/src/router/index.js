import { createRouter, createWebHistory } from 'vue-router'
import VentasView from '../views/VentasView.vue'
import AdminDashboardView from '../views/AdminDashboardView.vue'
import AdminStockView from '../views/AdminStockView.vue'
import AdminHomeView from '../views/AdminHomeView.vue'
import AdminAttendanceView from '../views/AdminAttendanceView.vue'
import AdminHistoryView from '../views/AdminHistoryView.vue'
import AdminReportsView from '../views/AdminReportsView.vue'
import AdminAuditView from '../views/AdminAuditView.vue'
import AdminOpenAccountsView from '../views/AdminOpenAccountsView.vue'
import {
  STORAGE_KEYS,
  limpiarAuthPersistida,
  normalizarSesionesValidas,
  obtenerRolGuardado,
  tokenExpirado,
} from '../utils/authSession'

const routes = [
  {
    path: '/',
    redirect: { name: 'login' },
  },
  {
    path: '/login',
    name: 'login',
    component: VentasView,
  },
  {
    path: '/panel',
    name: 'panel',
    component: VentasView,
    meta: { requiresAuth: true },
  },
  {
    path: '/historial',
    name: 'historial',
    component: VentasView,
    meta: { requiresAuth: true },
  },
  {
    path: '/admin-dashboard',
    component: AdminDashboardView,
    meta: { requiresAuth: true, requiresAdmin: true },
    children: [
      {
        path: '',
        name: 'admin-home',
        component: AdminHomeView,
      },
      {
        path: 'stock',
        name: 'admin-stock',
        component: AdminStockView,
      },
      {
        path: 'asistencia',
        name: 'admin-attendance',
        component: AdminAttendanceView,
      },
      {
        path: 'historial',
        name: 'admin-history',
        component: AdminHistoryView,
      },
      {
        path: 'reportes',
        name: 'admin-reports',
        component: AdminReportsView,
      },
      {
        path: 'cuentas-abiertas',
        name: 'admin-open-accounts',
        component: AdminOpenAccountsView,
      },
      {
        path: 'auditoria',
        name: 'admin-audit',
        component: AdminAuditView,
      },
    ],
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: { name: 'login' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior() {
    return { top: 0 }
  },
})

const existeSesionGuardada = () => {
  const sesionesValidas = normalizarSesionesValidas()
  if (sesionesValidas.length > 0) {
    return true
  }

  const tokenGuardado = localStorage.getItem(STORAGE_KEYS.token)
  const becadoGuardado = localStorage.getItem(STORAGE_KEYS.becado)
  if (!tokenGuardado || !becadoGuardado) {
    return false
  }

  if (tokenExpirado(tokenGuardado)) {
    limpiarAuthPersistida()
    return false
  }

  return true
}

router.beforeEach((to) => {
  if (!existeSesionGuardada()) {
    if (to.meta.requiresAuth || to.meta.requiresAdmin) {
      return { name: 'login' }
    }
    return true
  }

  if (to.meta.requiresAdmin) {
    if (obtenerRolGuardado() !== 'admin') {
      return { name: 'panel' }
    }
  }

  return true
})

export default router
