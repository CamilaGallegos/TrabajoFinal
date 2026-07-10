<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const ventasRecientes = ref([])
const cargandoVentas = ref(false)
const errorVentas = ref('')
const searchTerm = ref('')
const filtroTipoPago = ref('')
const filtroBecado = ref('')
const fechaDesde = ref('')
const fechaHasta = ref('')
const ventaDrawer = ref(null)
const feedback = ref({ show: false, message: '', type: 'success' })

const tiposPagoDisponibles = [
  { value: '', label: 'Sin filtro' },
  { value: 'efectivo', label: 'Efectivo' },
  { value: 'transferencia', label: 'Transferencia' },
  { value: 'combinado', label: 'Combinado' },
  { value: 'cuenta_abierta', label: 'Cuenta abierta' },
]

const becadosUnicos = computed(() => {
  const mapa = new Map()
  for (const venta of ventasRecientes.value) {
    if (venta.becado_nombre) {
      mapa.set(venta.becado_nombre, venta.becado_nombre)
    }
  }
  return Array.from(mapa.values())
})

const mostrarFeedback = (message, type = 'success') => {
  feedback.value = { show: true, message, type }
  window.clearTimeout(mostrarFeedback.timeout)
  mostrarFeedback.timeout = window.setTimeout(() => {
    feedback.value.show = false
  }, 2500)
}

const parsearFecha = (valor) => {
  if (!valor) return null
  const fecha = new Date(valor)
  return Number.isNaN(fecha.getTime()) ? null : fecha
}

const ventasFiltradas = computed(() => {
  return ventasRecientes.value
    .filter((venta) => {
      if (filtroTipoPago.value && venta.tipo_pago !== filtroTipoPago.value) {
        return false
      }
      if (filtroBecado.value && venta.becado_nombre !== filtroBecado.value) {
        return false
      }
      if (fechaDesde.value) {
        const desde = parsearFecha(fechaDesde.value)
        const ventaFecha = parsearFecha(venta.fecha)
        if (desde && ventaFecha && ventaFecha < desde) {
          return false
        }
      }
      if (fechaHasta.value) {
        const hasta = parsearFecha(fechaHasta.value)
        const ventaFecha = parsearFecha(venta.fecha)
        if (hasta && ventaFecha && ventaFecha > new Date(hasta.getTime() + 24 * 60 * 60 * 1000 - 1)) {
          return false
        }
      }
      if (searchTerm.value) {
        return textoCoincide(venta, searchTerm.value)
      }
      return true
    })
    .sort((a, b) => new Date(b.fecha) - new Date(a.fecha))
})

const textoCoincide = (venta, texto) => {
  const valor = [
    String(venta.id),
    venta.becado_nombre || '',
    venta.tipo_pago || '',
    venta.detalles?.map((detalle) => detalle.producto_nombre).join(' '),
    String(venta.total),
  ].join(' ').toLowerCase()
  return valor.includes(texto.toLowerCase())
}

const formatearFechaVenta = (fecha) => {
  const d = new Date(fecha)
  return d.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const obtenerVentas = async () => {
  cargandoVentas.value = true
  errorVentas.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/ventas/')
    ventasRecientes.value = Array.isArray(respuesta.data) ? respuesta.data : []
  } catch (error) {
    ventasRecientes.value = []
    errorVentas.value = 'No se pudo cargar el historial de ventas'
  } finally {
    cargandoVentas.value = false
  }
}

const abrirDetalles = (venta) => {
  ventaDrawer.value = venta
}

const cerrarDrawer = () => {
  ventaDrawer.value = null
}

onMounted(obtenerVentas)
</script>

<template>
  <div class="history-container">
    <header class="history-header">
      <div>
        <h1>Historial de ventas</h1>
        <p>Consulta el registro de todas las ventas realizadas en el sistema</p>
      </div>
    </header>

    <div v-if="feedback.show" class="feedback-banner" :class="feedback.type">
      {{ feedback.message }}
    </div>

    <section class="history-filters-card">
      <div class="filtros-grid">
        <div class="filtro-item filtro-buscar">
          <label for="searchTerm">Buscar</label>
          <input
            id="searchTerm"
            v-model="searchTerm"
            type="text"
            placeholder="Becada/o, producto, ID..."
          />
        </div>
        <div class="filtro-item">
          <label for="filtroTipoPago">Tipo de pago</label>
          <select id="filtroTipoPago" v-model="filtroTipoPago">
            <option v-for="opcion in tiposPagoDisponibles" :key="opcion.value" :value="opcion.value">
              {{ opcion.label }}
            </option>
          </select>
        </div>
        <div class="filtro-item">
          <label for="filtroBecado">Becado/a</label>
          <select id="filtroBecado" v-model="filtroBecado">
            <option value="">Sin filtro</option>
            <option v-for="becado in becadosUnicos" :key="becado" :value="becado">
              {{ becado }}
            </option>
          </select>
        </div>
        <div class="filtro-item">
          <label for="fechaDesde">Desde</label>
          <input id="fechaDesde" v-model="fechaDesde" type="date" />
        </div>
        <div class="filtro-item">
          <label for="fechaHasta">Hasta</label>
          <input id="fechaHasta" v-model="fechaHasta" type="date" />
        </div>
      </div>
    </section>

    <section class="history-table-card">
      <div v-if="cargandoVentas" class="history-loading">Cargando ventas...</div>
      <div v-else-if="errorVentas" class="history-error">{{ errorVentas }}</div>
      <div v-else-if="ventasFiltradas.length === 0" class="history-empty">
        No se encontraron ventas con esos filtros
      </div>
      <table v-else class="history-table">
        <tbody>
          <tr v-for="venta in ventasFiltradas" :key="venta.id" class="history-row">
            <td class="col-id">#{{ venta.id }}</td>
            <td class="col-fecha">{{ formatearFechaVenta(venta.fecha) }}</td>
            <td class="col-becado">{{ venta.becado_nombre || 'Sin nombre' }}</td>
            <td class="col-total">Total: ${{ Number(venta.total).toFixed(2) }}</td>
            <td class="col-pago">{{ venta.tipo_pago }}</td>
            <td class="col-acciones">
              <button type="button" class="btn-historial btn-detalles" @click="abrirDetalles(venta)">
                Ver detalles
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <Teleport to="body">
      <div v-if="ventaDrawer" class="drawer-overlay" @click.self="cerrarDrawer">
        <aside class="drawer">
          <div class="drawer__header">
            <h3>Venta #{{ ventaDrawer.id }}</h3>
            <button type="button" class="drawer__close" @click="cerrarDrawer">✕</button>
          </div>

          <div class="drawer__body">
            <dl class="drawer-info">
              <dt>Fecha</dt>
              <dd>{{ formatearFechaVenta(ventaDrawer.fecha) }}</dd>
              <dt>Becado/a</dt>
              <dd>{{ ventaDrawer.becado_nombre || 'Sin nombre' }}</dd>
              <dt>Tipo de pago</dt>
              <dd>{{ ventaDrawer.tipo_pago }}</dd>
              <template v-if="ventaDrawer.tipo_pago === 'combinado' || ventaDrawer.tipo_pago === 'efectivo'">
                <dt>Efectivo</dt>
                <dd>${{ Number(ventaDrawer.monto_efectivo).toFixed(2) }}</dd>
              </template>
              <template v-if="ventaDrawer.tipo_pago === 'combinado' || ventaDrawer.tipo_pago === 'transferencia'">
                <dt>Transferencia</dt>
                <dd>${{ Number(ventaDrawer.monto_transferencia).toFixed(2) }}</dd>
              </template>
              <template v-if="ventaDrawer.cuenta_abierta">
                <dt>Cuenta abierta</dt>
                <dd>{{ ventaDrawer.cuenta_abierta }}</dd>
              </template>
              <dt>Total</dt>
              <dd class="total-highlight">${{ Number(ventaDrawer.total).toFixed(2) }}</dd>
            </dl>

            <h4>Productos</h4>
            <table class="drawer-table">
              <thead>
                <tr>
                  <th>Producto</th>
                  <th class="right">Cant.</th>
                  <th class="right">P. Unit.</th>
                  <th class="right">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="detalle in ventaDrawer.detalles" :key="detalle.producto_nombre">
                  <td>{{ detalle.producto_nombre }}</td>
                  <td class="right">{{ detalle.cantidad }}</td>
                  <td class="right">${{ Number(detalle.precio_unitario).toFixed(2) }}</td>
                  <td class="right">
                    ${{ (detalle.cantidad * Number(detalle.precio_unitario)).toFixed(2) }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.history-container {
  width: 100%;
  display: grid;
  gap: 20px;
}

.history-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #d8dde6;
}

.history-header h1 {
  margin: 0 0 8px;
  color: #08324a;
  font-size: clamp(1.5rem, 2vw, 2rem);
}

.history-header p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
  max-width: 640px;
}

.feedback-banner {
  padding: 12px 14px;
  border-radius: 10px;
  font-weight: 600;
  font-size: 14px;
  border: 1px solid transparent;
}

.feedback-banner.success {
  background: #ecfdf3;
  color: #166534;
  border-color: #a7f3d0;
}

.feedback-banner.error {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fecaca;
}

.history-filters-card {
  background: #ffffff;
  border: 1px solid #d8dde6;
  border-radius: 16px;
  padding: 16px;
}

.filtros-grid {
  display: grid;
  grid-template-columns: 1fr 140px 140px 120px 120px;
  gap: 8px;
  align-items: end;
}

.filtro-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filtro-buscar {
  grid-column: 1 / 2;
}

.filtro-item label {
  font-size: 11px;
  color: #475569;
  text-transform: uppercase;
  font-weight: 600;
}

.filtro-item input,
.filtro-item select {
  padding: 8px 10px;
  border: 1px solid #d8dde6;
  border-radius: 8px;
  font-size: 13px;
  background: #ffffff;
}

.filtro-item input:focus,
.filtro-item select:focus {
  outline: none;
  border-color: #0578af;
  box-shadow: 0 0 0 3px rgba(5, 120, 175, 0.1);
}

.history-table-card {
  width: 100%;
  background: #ffffff;
  border: 1px solid #d8dee7;
  border-radius: 16px;
  overflow: hidden;
}

.history-loading,
.history-error,
.history-empty {
  padding: 28px;
  color: #475569;
  text-align: center;
  font-size: 14px;
}

.history-error {
  color: #dc2626;
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-row {
  border-bottom: 1px solid #eef2f7;
}

.history-row:last-child {
  border-bottom: none;
}

.history-row td {
  padding: 12px 14px;
  font-size: 13px;
  color: #475569;
}

.col-id {
  color: #0578af;
  font-weight: 600;
  min-width: 60px;
}

.col-fecha {
  color: #64748b;
  font-size: 12px;
  min-width: 160px;
}

.col-becado {
  min-width: 140px;
}

.col-total {
  font-weight: 600;
  color: #0f172a;
}

.col-pago {
  text-transform: capitalize;
  color: #64748b;
  font-size: 12px;
}

.col-acciones {
  text-align: right;
  min-width: 140px;
}

.btn-historial {
  border: 1px solid #0578af;
  background: transparent;
  color: #0578af;
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-historial:hover {
  background: #e8f3fb;
}

.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 40;
  animation: fadeIn 0.2s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.drawer {
  position: fixed;
  top: 0;
  right: 0;
  width: min(480px, 90vw);
  height: 100vh;
  background: #ffffff;
  box-shadow: -2px 0 20px rgba(0, 0, 0, 0.2);
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease-out;
  z-index: 41;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #e2e8f0;
}

.drawer__header h3 {
  margin: 0;
  color: #0f172a;
  font-size: 18px;
}

.drawer__close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #64748b;
}

.drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.drawer-info {
  display: grid;
  grid-template-columns: 100px 1fr;
  gap: 12px 16px;
  margin-bottom: 20px;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 16px;
}

.drawer-info dt {
  font-weight: 600;
  color: #64748b;
  font-size: 12px;
  text-transform: uppercase;
}

.drawer-info dd {
  margin: 0;
  color: #0f172a;
}

.total-highlight {
  font-weight: 600;
  color: #0578af;
  font-size: 16px;
}

.drawer__body h4 {
  margin: 20px 0 12px;
  color: #0f172a;
  font-size: 14px;
}

.drawer-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.drawer-table thead {
  background: #f1f8ff;
}

.drawer-table th {
  padding: 8px;
  text-align: left;
  font-weight: 600;
  color: #0f172a;
  border-bottom: 1px solid #e2e8f0;
}

.drawer-table td {
  padding: 8px;
  border-bottom: 1px solid #eef2f7;
  color: #475569;
}

.drawer-table .right {
  text-align: right;
}

@media (max-width: 760px) {
  .filtros-grid {
    grid-template-columns: 1fr;
  }

  .drawer {
    width: 100vw;
  }
}
</style>
