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
  const sesionesRaw = localStorage.getItem('sigfo_sesiones')
  if (sesionesRaw) {
    try {
      const sesiones = JSON.parse(sesionesRaw)
      if (Array.isArray(sesiones) && sesiones.length > 0) {
        return true
      }
    } catch {
    }
  }

  const tokenGuardado = localStorage.getItem('sigfo_token')
  const becadoGuardado = localStorage.getItem('sigfo_becado')
  return Boolean(tokenGuardado && becadoGuardado)
}

const obtenerRolGuardado = () => {
  if (localStorage.getItem('sigfo_role') === 'admin') {
    return 'admin'
  }

  const sesionesRaw = localStorage.getItem('sigfo_sesiones')
  if (sesionesRaw) {
    try {
      const sesiones = JSON.parse(sesionesRaw)
      if (Array.isArray(sesiones)) {
        const sesionAdmin = sesiones.find((sesion) => sesion.role === 'admin' || sesion.isAdmin)
        if (sesionAdmin) {
          return 'admin'
        }
      }
    } catch {
    }
  }

  return 'becado'
}

router.beforeEach((to) => {
  if (to.meta.requiresAdmin) {
    if (!existeSesionGuardada()) {
      return { name: 'login' }
    }

    if (obtenerRolGuardado() !== 'admin') {
      return { name: 'panel' }
    }
  }

  if (to.meta.requiresAuth) {
    if (!existeSesionGuardada()) {
      return { name: 'login' }
    }
  }

  return true
})

export default router
