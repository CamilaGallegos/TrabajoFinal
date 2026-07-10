<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'

const actividad = ref([])
const ventasHoy = ref([])
const cargando = ref(false)
const error = ref('')
const errorResumen = ref('')
let refreshId = null

const formatoMoneda = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  minimumFractionDigits: 2,
})

const formatearTiempo = (fechaIso) => {
  if (!fechaIso) return 'hace un momento'
  const fecha = new Date(fechaIso)
  const diffMs = Date.now() - fecha.getTime()
  const diffMin = Math.max(1, Math.floor(diffMs / (1000 * 60)))

  if (diffMin < 60) {
    return `hace ${diffMin} minuto${diffMin === 1 ? '' : 's'}`
  }

  const diffHoras = Math.floor(diffMin / 60)
  if (diffHoras < 24) {
    return `hace ${diffHoras} hora${diffHoras === 1 ? '' : 's'}`
  }

  const diffDias = Math.floor(diffHoras / 24)
  return `hace ${diffDias} día${diffDias === 1 ? '' : 's'}`
}

const sesionesPresentacion = computed(() => {
  return actividad.value.map((item) => {
    if (item.estado === 'activo') {
      return {
        ...item,
        estadoTexto: 'activo ahora',
      }
    }
    return {
      ...item,
      estadoTexto: `activo ${formatearTiempo(item.ultima_actividad)}`,
    }
  })
})

const esMismoDiaLocal = (fechaIso) => {
  const fecha = new Date(fechaIso)
  const ahora = new Date()
  return (
    fecha.getFullYear() === ahora.getFullYear() &&
    fecha.getMonth() === ahora.getMonth() &&
    fecha.getDate() === ahora.getDate()
  )
}

const resumenDiario = computed(() => {
  let totalEfectivo = 0
  let totalTransferencia = 0

  const ventas = ventasHoy.value.filter((venta) => esMismoDiaLocal(venta.fecha))
  for (const venta of ventas) {
    totalEfectivo += Number(venta.monto_efectivo || 0)
    totalTransferencia += Number(venta.monto_transferencia || 0)
  }

  return {
    cantidadVentas: ventas.length,
    totalEfectivo,
    totalTransferencia,
    totalGeneral: totalEfectivo + totalTransferencia,
  }
})

const resumenDiarioPresentacion = computed(() => ({
  cantidadVentas: resumenDiario.value.cantidadVentas,
  totalEfectivo: formatoMoneda.format(resumenDiario.value.totalEfectivo),
  totalTransferencia: formatoMoneda.format(resumenDiario.value.totalTransferencia),
  totalGeneral: formatoMoneda.format(resumenDiario.value.totalGeneral),
}))

const obtenerActividad = async () => {
  cargando.value = true
  error.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/fichaje/actividad/', {
      params: { _: Date.now() },
    })
    actividad.value = Array.isArray(respuesta.data) ? respuesta.data : []
  } catch (err) {
    actividad.value = []
    if (err.response?.status === 403) {
      error.value = 'No autorizado para ver actividad de sesiones'
    } else if (err.response?.status === 401) {
      error.value = 'Sesión expirada, vuelve a iniciar sesión'
    } else {
      error.value = 'No se pudo cargar la actividad de sesiones'
    }
  } finally {
    cargando.value = false
  }
}

const obtenerVentasDelDia = async () => {
  errorResumen.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/ventas/', {
      params: { _: Date.now() },
    })
    ventasHoy.value = Array.isArray(respuesta.data) ? respuesta.data : []
  } catch (err) {
    ventasHoy.value = []
    errorResumen.value = 'No se pudo cargar el resumen de ventas del día'
  }
}

const refrescarInicio = async () => {
  await Promise.all([obtenerActividad(), obtenerVentasDelDia()])
}

onMounted(() => {
  refrescarInicio()
  refreshId = window.setInterval(refrescarInicio, 30000)
})

onBeforeUnmount(() => {
  if (refreshId) {
    window.clearInterval(refreshId)
    refreshId = null
  }
})
</script>

<template>
  <div class="content-box">
    <header class="home-header">
      <div>
        <h2>Inicio</h2>
        <p>Sesiones activas y resumen de ventas del día</p>
      </div>
      <button type="button" class="btn-refresh" @click="refrescarInicio">Actualizar</button>
    </header>

    <section class="resumen-grid">
      <article class="resumen-card">
        <h3>Ventas del día</h3>
        <p>{{ resumenDiarioPresentacion.cantidadVentas }}</p>
      </article>
      <article class="resumen-card">
        <h3>Total en efectivo</h3>
        <p>{{ resumenDiarioPresentacion.totalEfectivo }}</p>
      </article>
      <article class="resumen-card">
        <h3>Total en transferencia</h3>
        <p>{{ resumenDiarioPresentacion.totalTransferencia }}</p>
      </article>
      <article class="resumen-card total">
        <h3>Total del día</h3>
        <p>{{ resumenDiarioPresentacion.totalGeneral }}</p>
      </article>
    </section>

    <div v-if="errorResumen" class="estado-msg error">{{ errorResumen }}</div>

    <div v-if="cargando" class="estado-msg">Cargando actividad...</div>
    <div v-else-if="error" class="estado-msg error">{{ error }}</div>
    <div v-else-if="sesionesPresentacion.length === 0" class="estado-msg">
      No hay actividad registrada en las últimas 48 horas
    </div>
    <ul v-else class="sesiones-lista">
      <li v-for="sesion in sesionesPresentacion" :key="sesion.becado_id" class="sesion-item">
        <span class="sesion-nombre">{{ sesion.nombre_usuario }}</span>
        <span :class="['sesion-estado', sesion.estado === 'activo' ? 'activo' : 'cerrada']">
          {{ sesion.estadoTexto }}
        </span>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.content-box {
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #d8dde6;
  display: grid;
  gap: 14px;
}

.home-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.content-box h2 {
  margin: 0 0 8px;
  color: #08324a;
}

.content-box p {
  margin: 0;
  color: #5b6b79;
}

.btn-refresh {
  border: 0;
  border-radius: 10px;
  padding: 8px 12px;
  background: #0578af;
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
}

.btn-refresh:hover {
  background: #046892;
}

.estado-msg {
  color: #5b6b79;
  font-size: 14px;
}

.estado-msg.error {
  color: #b91c1c;
}

.resumen-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(170px, 1fr));
  gap: 10px;
}

.resumen-card {
  border: 1px solid #d8e2ee;
  border-radius: 10px;
  background: #f8fbfd;
  padding: 12px;
}

.resumen-card h3 {
  margin: 0;
  font-size: 12px;
  font-weight: 700;
  color: #475569;
  text-transform: uppercase;
}

.resumen-card p {
  margin: 8px 0 0;
  color: #0f172a;
  font-weight: 700;
  font-size: 20px;
}

.resumen-card.total {
  border-color: #8ec5de;
  background: #e9f5fb;
}

.sesiones-lista {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.sesion-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  background: #f8fbfd;
}

.sesion-nombre {
  font-weight: 600;
  color: #0f172a;
}

.sesion-estado {
  font-size: 13px;
  font-weight: 600;
}

.sesion-estado.activo {
  color: #047857;
}

.sesion-estado.cerrada {
  color: #334155;
}

@media (max-width: 980px) {
  .resumen-grid {
    grid-template-columns: repeat(2, minmax(170px, 1fr));
  }
}

@media (max-width: 560px) {
  .resumen-grid {
    grid-template-columns: 1fr;
  }
}
</style>
