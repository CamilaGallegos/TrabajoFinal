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

const decodificarPayloadJWT = (jwtToken) => {
  try {
    const payloadBase64 = jwtToken.split('.')[1]
    const payloadNormalizado = payloadBase64.replace(/-/g, '+').replace(/_/g, '/')
    const payloadJson = decodeURIComponent(
      atob(payloadNormalizado)
        .split('')
        .map((c) => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`)
        .join('')
    )
    return JSON.parse(payloadJson)
  } catch {
    return null
  }
}

const tokenExpirado = (jwtToken) => {
  const payload = decodificarPayloadJWT(jwtToken)
  const exp = payload?.exp
  if (!exp) {
    return true
  }
  return (exp * 1000) <= Date.now()
}

const limpiarAuthPersistida = () => {
  localStorage.removeItem('sigfo_token')
  localStorage.removeItem('sigfo_becado')
  localStorage.removeItem('sigfo_role')
  localStorage.removeItem('sigfo_sesiones')
}

const normalizarSesionesValidas = () => {
  const sesionesRaw = localStorage.getItem('sigfo_sesiones')
  if (!sesionesRaw) {
    return []
  }

  try {
    const sesiones = JSON.parse(sesionesRaw)
    if (!Array.isArray(sesiones)) {
      return []
    }

    const validas = sesiones.filter((sesion) => sesion?.token && !tokenExpirado(sesion.token))
    if (validas.length !== sesiones.length) {
      if (validas.length > 0) {
        localStorage.setItem('sigfo_sesiones', JSON.stringify(validas))
      } else {
        localStorage.removeItem('sigfo_sesiones')
      }
    }
    return validas
  } catch {
    localStorage.removeItem('sigfo_sesiones')
    return []
  }
}

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

  const tokenGuardado = localStorage.getItem('sigfo_token')
  const becadoGuardado = localStorage.getItem('sigfo_becado')
  if (!tokenGuardado || !becadoGuardado) {
    return false
  }

  if (tokenExpirado(tokenGuardado)) {
    limpiarAuthPersistida()
    return false
  }

  return true
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
