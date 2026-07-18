<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const fechaDesde = ref('')
const fechaHasta = ref('')
const cargando = ref(false)
const error = ref('')
const cuentas = ref([])
const cuentasExpandida = ref({})

const formatMoney = (value) => {
  const number = Number(value || 0)
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    minimumFractionDigits: 2,
  }).format(number)
}

const formatDateTime = (isoDate) => {
  if (!isoDate) {
    return '-'
  }
  const date = new Date(isoDate)
  return date.toLocaleString('es-AR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const cuentaKey = (cuentaId) => `cuenta-${cuentaId}`

const cuentaExpandida = (cuentaId) => Boolean(cuentasExpandida.value[cuentaKey(cuentaId)])

const toggleCuentaExpandida = (cuentaId) => {
  const key = cuentaKey(cuentaId)
  cuentasExpandida.value[key] = !cuentasExpandida.value[key]
}

const ventasVisibles = (cuenta) => {
  if (cuentaExpandida(cuenta.cuenta_id)) {
    return cuenta.ventas
  }
  return cuenta.ventas.slice(0, 5)
}

const puedeExpandir = (cuenta) => (cuenta.ventas?.length || 0) > 5

const hayFiltroActivo = computed(() => Boolean(fechaDesde.value || fechaHasta.value))

const cargarResumen = async () => {
  cargando.value = true
  error.value = ''

  try {
    const params = {
      _: Date.now(),
    }
    if (fechaDesde.value) {
      params.fecha_desde = fechaDesde.value
    }
    if (fechaHasta.value) {
      params.fecha_hasta = fechaHasta.value
    }

    const response = await axios.get('http://localhost:8000/api/cuentas-abiertas-resumen/', { params })
    cuentas.value = response.data?.cuentas || []
    cuentasExpandida.value = {}
  } catch (err) {
    cuentas.value = []
    error.value = 'No se pudo cargar el resumen de cuentas abiertas'
  } finally {
    cargando.value = false
  }
}

const limpiarFiltros = () => {
  fechaDesde.value = ''
  fechaHasta.value = ''
  cargarResumen()
}

onMounted(() => {
  cargarResumen()
})
</script>

<template>
  <div class="open-accounts-container">
    <header class="open-accounts-header">
      <div>
        <h2>Cuentas abiertas</h2>
      </div>

      <div class="filters-actions">
        <label>
          Desde
          <input v-model="fechaDesde" type="date" />
        </label>

        <label>
          Hasta
          <input v-model="fechaHasta" type="date" />
        </label>

        <button type="button" class="btn-refresh" @click="cargarResumen">Aplicar filtro</button>
        <button v-if="hayFiltroActivo" type="button" class="btn-secondary" @click="limpiarFiltros">
          Limpiar
        </button>
      </div>
    </header>

    <div v-if="cargando" class="estado-msg">Cargando cuentas abiertas...</div>
    <div v-else-if="error" class="estado-msg error">{{ error }}</div>

    <section v-else class="cuentas-grid">
      <div v-if="cuentas.length === 0" class="estado-msg">No hay cuentas abiertas para mostrar.</div>

      <article v-for="cuenta in cuentas" :key="cuenta.cuenta_id" class="cuenta-card">
        <header class="cuenta-header">
          <div>
            <h3>{{ cuenta.nombre_departamento }}</h3>
            <p v-if="cuenta.responsable">Responsable: {{ cuenta.responsable }}</p>
          </div>

          <div class="cuenta-metricas">
            <strong>{{ formatMoney(cuenta.total_ventas) }}</strong>
            <small>{{ cuenta.cantidad_ventas }} ventas</small>
          </div>
        </header>

        <div v-if="cuenta.ventas.length === 0" class="estado-msg">
          No hay ventas para esta cuenta en el rango seleccionado.
        </div>

        <table v-else class="ventas-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Becado</th>
              <th>Tipo de pago</th>
              <th class="right">Total</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="venta in ventasVisibles(cuenta)" :key="venta.id">
              <td>{{ formatDateTime(venta.fecha) }}</td>
              <td>{{ venta.becado_nombre }}</td>
              <td>{{ venta.tipo_pago }}</td>
              <td class="right">{{ formatMoney(venta.total) }}</td>
            </tr>
          </tbody>
        </table>

        <div v-if="puedeExpandir(cuenta)" class="cuenta-footer">
          <button type="button" class="btn-link" @click="toggleCuentaExpandida(cuenta.cuenta_id)">
            {{ cuentaExpandida(cuenta.cuenta_id) ? 'Ver menos' : 'Ver mas' }}
          </button>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.open-accounts-container {
  width: 100%;
  display: grid;
  gap: 18px;
}

.open-accounts-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #d8dde6;
}

.open-accounts-header h2 {
  margin: 0 0 8px;
  color: #08324a;
}

.open-accounts-header p {
  margin: 0;
  color: #5b6b79;
}

.filters-actions {
  display: flex;
  align-items: end;
  gap: 10px;
  flex-wrap: wrap;
}

.filters-actions label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.filters-actions input {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 10px;
  color: #0f172a;
}

.btn-refresh,
.btn-secondary {
  border: 0;
  border-radius: 10px;
  padding: 9px 14px;
  font-weight: 700;
  cursor: pointer;
}

.btn-refresh {
  background: #0077b6;
  color: #ffffff;
}

.btn-refresh:hover {
  background: #04689f;
}

.btn-secondary {
  background: #e2e8f0;
  color: #0f172a;
}

.btn-secondary:hover {
  background: #cbd5e1;
}

.estado-msg {
  color: #5b6b79;
  font-size: 14px;
}

.estado-msg.error {
  color: #b91c1c;
}

.cuentas-grid {
  display: grid;
  gap: 14px;
}

.cuenta-card {
  border: 1px solid #d8dde6;
  border-radius: 16px;
  padding: 16px;
  background: #ffffff;
}

.cuenta-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.cuenta-header h3 {
  margin: 0 0 4px;
  color: #0f172a;
}

.cuenta-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.cuenta-metricas {
  text-align: right;
  display: grid;
  gap: 4px;
}

.cuenta-metricas strong {
  color: #0578af;
  font-size: 18px;
}

.cuenta-metricas small {
  color: #64748b;
}

.ventas-table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border-radius: 10px;
  overflow: hidden;
}

.ventas-table th,
.ventas-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eef2f7;
  font-size: 13px;
  color: #334155;
  text-align: left;
}

.ventas-table th {
  background: #eef7fb;
  color: #0f172a;
  font-size: 12px;
  text-transform: uppercase;
}

.ventas-table .right {
  text-align: right;
}

.cuenta-footer {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.btn-link {
  border: 0;
  background: transparent;
  color: #0578af;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 0;
}

.btn-link:hover {
  color: #046892;
  text-decoration: underline;
}

@media (max-width: 900px) {
  .open-accounts-header,
  .cuenta-header {
    flex-direction: column;
  }

  .filters-actions {
    width: 100%;
  }

  .cuenta-metricas {
    text-align: left;
  }

  .ventas-table {
    display: block;
    overflow-x: auto;
  }
}
</style>
