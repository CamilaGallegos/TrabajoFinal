<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const route = useRoute()

const secciones = [
  { id: 'inicio', label: 'Inicio', route: 'admin-home' },
  { id: 'asistencia', label: 'Asistencia', route: 'admin-attendance' },
  { id: 'stock', label: 'Productos', route: 'admin-stock' },
  { id: 'historial', label: 'Historial de ventas', route: 'admin-history' },
  { id: 'auditoria', label: 'Auditoría', route: 'admin-audit' },
  { id: 'cuentas-abiertas', label: 'Cuenta abiertas', route: 'admin-open-accounts' },
  { id: 'reportes', label: 'Estadísticas', route: 'admin-reports' },
]

const seleccionarSeccion = (item) => {
  router.push({ name: item.route })
}

const activeSection = computed(() => {
  const mapping = {
    'admin-home': 'inicio',
    'admin-attendance': 'asistencia',
    'admin-stock': 'stock',
    'admin-history': 'historial',
    'admin-open-accounts': 'cuentas-abiertas',
    'admin-audit': 'auditoria',
    'admin-reports': 'reportes',
  }
  return mapping[route.name] || 'inicio'
})

const sectionLabel = computed(() => {
  return secciones.find((item) => item.id === activeSection.value)?.label || 'Inicio'
})

const volverAlPanel = () => {
  router.push({ name: 'panel' })
}

const cerrarSesion = () => {
  // limpia el almacenamiento local y header de auth
  try {
    localStorage.removeItem('sigfo_token')
    localStorage.removeItem('sigfo_becado')
    localStorage.removeItem('sigfo_role')
    localStorage.removeItem('sigfo_sesiones')
  } catch (e) {
  }
  delete axios.defaults.headers.common.Authorization
  router.push({ name: 'login' })
  try {
    window.location.reload()
  } catch (e) {
  }
}
</script>

<template>
  <div class="admin-shell">
    <header class="admin-header">
      <div class="header-left">
        <h1 class="brand-title">SiGFo CURZAS</h1>
        <p class="brand-subtitle">Sistema de Gestión de la Fotocopiadora del CURZAS</p>
      </div>
        <div class="header-right">
          <button type="button" class="btn-add" @click="volverAlPanel">Volver al panel de ventas</button>
              <button type="button" class="btn-danger" @click="cerrarSesion">Cerrar Sesión</button>
        </div>
    </header>

    <section class="admin-nav-tabs">
      <button
        v-for="item in secciones"
        :key="item.id"
        type="button"
        :class="['nav-tab', { active: item.id === activeSection }]"
        @click="seleccionarSeccion(item)"
      >
        {{ item.label }}
      </button>
    </section>

    <section class="admin-content">
      <router-view />
    </section>
  </div>
</template>

<style scoped>
:root {
  color-scheme: light;
}

.admin-shell {
  width: 100%;
  max-width: none;
  margin: 0;
  min-height: 100vh;
  display: grid;
  grid-template-rows: auto auto 1fr;
  gap: 0;
  padding: clamp(12px, 1.8vw, 26px);
  background: #ffffff; 
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #1f2937;
}

.admin-header {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 14px 18px;
  background: linear-gradient(90deg, #0578af 0%, #0d8bc8 55%, #0578af 100%);
  color: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 10px 28px rgba(5, 120, 175, 0.18);
}

.header-left {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.brand-title {
  margin: 0;
  color: #ffffff;
  font-size: clamp(20px, 1.7vw, 26px);
  font-weight: 800;
  letter-spacing: 0.4px;
}

.brand-subtitle {
  margin: 0;
  color: rgba(255, 255, 255, 0.82);
  font-size: 12px;
  font-weight: 400;
}

.header-right {
  flex: 0 0 auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
}

.btn-primary {
  border: none;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  background: #ffffff;
  color: #045b84;
  transition: opacity 0.2s ease;
}

.btn-primary:hover {
  opacity: 0.9;
  transform: none;
}

.btn-danger {
  border: none;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #c53030;
  color: #ffffff;
  transition: opacity 0.2s ease;
}

.btn-danger:hover {
  opacity: 0.9;
  transform: none;
  box-shadow: none;
}

.btn-add {
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  padding: 8px 12px;
  background: #ffffff;
  color: #045b84;
}

.admin-nav-tabs {
  display: flex;
  gap: 10px;
  background: transparent;
  border-bottom: none;
  padding: 0;
  margin: 16px 0 18px;
  overflow-x: auto;
}

.nav-tab {
  border: 1px solid #b7cad8;
  background: #ffffff;
  color: #045b84;
  border-radius: 999px;
  padding: 9px 14px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  margin-bottom: 0;
  white-space: nowrap;
}

.nav-tab:hover {
  background: #e8f3fb;
  color: #045b84;
}

.nav-tab.active {
  background: #0578af;
  color: #ffffff;
  border-color: #0578af;
}

.admin-content {
  padding: 8px 0 0; 
}

.content-box {
  padding: 18px;
  border-radius: 14px;
  background: #ffffff;
  border: 1px solid #d8dde6;
  box-shadow: none;
  max-width: none;
}

.content-box h2 {
  margin: 0 0 14px;
  color: #08324a;
  font-size: 20px;
  font-weight: 700;
}

.content-box p {
  margin: 4px 0 0;
  color: #5b6b79;
  font-size: 14px;
  line-height: 1.5;
}

@media (max-width: 1200px) {
}

@media (max-width: 640px) {
  .admin-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    position: static;
  }

  .header-center {
    align-items: flex-start;
    text-align: left;
  }

  .header-right {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
