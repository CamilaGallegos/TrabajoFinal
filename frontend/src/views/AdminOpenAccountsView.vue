<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'
import * as XLSX from 'xlsx'
import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

const fechaDesde = ref('')
const fechaHasta = ref('')
const cargando = ref(false)
const error = ref('')
const cuentas = ref([])
const cuentaSeleccionadaId = ref('')
const cuentasExpandida = ref({})
const exportando = ref({})
const modalPagoAbierto = ref(false)
const modalHistorialAbierto = ref(false)
const registrandoPago = ref(false)
const errorPago = ref('')
const pagoExpandidoId = ref(null)

const pagoForm = ref({
  monto: '',
  metodo_pago: 'transferencia',
  fecha_pago: '',
  referencia: '',
  observaciones: '',
})

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

const formatTipoPago = (value) => {
  if (!value) {
    return '-'
  }
  return String(value)
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase())
}

const formatDateInputValue = (date = new Date()) => {
  const local = new Date(date.getTime() - (date.getTimezoneOffset() * 60000))
  return local.toISOString().slice(0, 16)
}

const toApiDateTime = (value) => {
  if (!value) {
    return null
  }
  return new Date(value).toISOString()
}

// Limpia texto para usarlo como nombre de archivo
const sanitizeFileName = (value) => {
  return String(value || 'cuenta')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-zA-Z0-9-_]/g, '_')
}

const rangoTextoExport = computed(() => {
  const desde = fechaDesde.value || 'Sin fecha desde'
  const hasta = fechaHasta.value || 'Sin fecha hasta'
  if (!fechaDesde.value && !fechaHasta.value) {
    return 'Sin filtro de fechas'
  }
  return `${desde} al ${hasta}`
})

const exportingKey = (cuentaId, tipo) => `cuenta-${cuentaId}-${tipo}`

const estaExportando = (cuentaId, tipo) => Boolean(exportando.value[exportingKey(cuentaId, tipo)])

// Actualiza el estado de exportacion para habilitar/deshabilitar botones
const setExportando = (cuentaId, tipo, value) => {
  exportando.value[exportingKey(cuentaId, tipo)] = value
}

const ventaDetallesTexto = (venta) => {
  const detalles = Array.isArray(venta.detalles) ? venta.detalles : []
  if (detalles.length === 0) {
    return '-'
  }

  return detalles
    .map((detalle) => `${detalle.cantidad} x ${detalle.producto_nombre}`)
    .join(' | ')
}

const exportarExcelCuenta = (cuenta) => {
  setExportando(cuenta.cuenta_id, 'excel', true)
  try {
    const wsData = [
      ['Cuenta abierta', cuenta.nombre_departamento],
      ['Responsable', cuenta.responsable || '-'],
      ['Rango aplicado', rangoTextoExport.value],
      ['Total cuenta', Number(cuenta.total_ventas || 0)],
      ['Total pendiente', Number(cuenta.total_pendiente || 0)],
      ['Total pagado', Number(cuenta.total_pagado || 0)],
      ['Cantidad de ventas', cuenta.cantidad_ventas || 0],
      [],
      ['Venta ID', 'Fecha', 'Becado', 'Total', 'Saldo', 'Detalle'],
    ]

    for (const venta of cuenta.ventas || []) {
      wsData.push([
        venta.id,
        formatDateTime(venta.fecha),
        venta.becado_nombre,
        Number(venta.total || 0),
        Number(venta.saldo || 0),
        ventaDetallesTexto(venta),
      ])
    }

    const workbook = XLSX.utils.book_new()
    const worksheet = XLSX.utils.aoa_to_sheet(wsData)
    worksheet['!cols'] = [
      { wch: 10 },
      { wch: 20 },
      { wch: 22 },
      { wch: 14 },
      { wch: 14 },
      { wch: 60 },
    ]

    XLSX.utils.book_append_sheet(workbook, worksheet, 'Cuenta abierta')
    const fileName = `cuenta_abierta_${sanitizeFileName(cuenta.nombre_departamento)}.xlsx`
    XLSX.writeFile(workbook, fileName)
  } finally {
    setExportando(cuenta.cuenta_id, 'excel', false)
  }
}

const exportarPdfCuenta = (cuenta) => {
  setExportando(cuenta.cuenta_id, 'pdf', true)
  try {
    const doc = new jsPDF({ orientation: 'landscape', unit: 'mm', format: 'a4' })
    doc.setFontSize(14)
    doc.text(`Cuenta abierta: ${cuenta.nombre_departamento}`, 14, 14)

    doc.setFontSize(10)
    doc.text(`Responsable: ${cuenta.responsable || '-'}`, 14, 21)
    doc.text(`Rango: ${rangoTextoExport.value}`, 14, 27)
    doc.text(`Total cuenta: ${formatMoney(cuenta.total_ventas)}`, 14, 33)
    doc.text(`Pendiente: ${formatMoney(cuenta.total_pendiente)} | Pagado: ${formatMoney(cuenta.total_pagado)}`, 14, 39)

    const body = (cuenta.ventas || []).map((venta) => ([
      venta.id,
      formatDateTime(venta.fecha),
      venta.becado_nombre,
      formatMoney(venta.total),
      formatMoney(venta.saldo),
      ventaDetallesTexto(venta),
    ]))

    autoTable(doc, {
      startY: 44,
      head: [['Venta ID', 'Fecha', 'Becado', 'Total', 'Saldo', 'Detalle']],
      body,
      styles: { fontSize: 8, cellPadding: 2 },
      headStyles: { fillColor: [5, 120, 175] },
      columnStyles: {
        0: { cellWidth: 16 },
        1: { cellWidth: 28 },
        2: { cellWidth: 38 },
        3: { cellWidth: 20 },
        4: { cellWidth: 20 },
        5: { cellWidth: 'auto' },
      },
    })

    const fileName = `cuenta_abierta_${sanitizeFileName(cuenta.nombre_departamento)}.pdf`
    doc.save(fileName)
  } finally {
    setExportando(cuenta.cuenta_id, 'pdf', false)
  }
}

// controla el "ver más" por cuenta
const cuentaKey = (cuentaId) => `cuenta-${cuentaId}`

const cuentaExpandida = (cuentaId) => Boolean(cuentasExpandida.value[cuentaKey(cuentaId)])

const toggleCuentaExpandida = (cuentaId) => {
  const key = cuentaKey(cuentaId)
  cuentasExpandida.value[key] = !cuentasExpandida.value[key]
}

const ventasVisibles = (cuenta) => {
  const ventas = cuenta?.ventas || []

  if (cuentaExpandida(cuenta.cuenta_id)) {
    return ventas
  }

  return ventas.slice(0, 5)
}

const puedeExpandir = (cuenta) => (cuenta.ventas?.length || 0) > 5

const hayFiltroActivo = computed(() => Boolean(fechaDesde.value || fechaHasta.value))

const cuentaSeleccionada = computed(() => {
  return cuentas.value.find((cuenta) => String(cuenta.cuenta_id) === String(cuentaSeleccionadaId.value)) || null
})

const opcionesCuentas = computed(() => {
  return cuentas.value.map((cuenta) => ({
    value: String(cuenta.cuenta_id),
    label: `${cuenta.nombre_departamento}`,
  }))
})

const sincronizarCuentaSeleccionada = () => {
  if (cuentas.value.length === 0) {
    cuentaSeleccionadaId.value = ''
    return
  }

  const existeSeleccion = cuentas.value.some(
    (cuenta) => String(cuenta.cuenta_id) === String(cuentaSeleccionadaId.value),
  )

  if (!existeSeleccion) {
    cuentaSeleccionadaId.value = String(cuentas.value[0].cuenta_id)
  }
}

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
    sincronizarCuentaSeleccionada()
  } catch (err) {
    cuentas.value = []
    cuentaSeleccionadaId.value = ''
    const apiError = err?.response?.data
    if (typeof apiError === 'string') {
      error.value = apiError
    } else if (apiError?.detail) {
      error.value = apiError.detail
    } else if (apiError?.non_field_errors?.[0]) {
      error.value = apiError.non_field_errors[0]
    } else {
      error.value = 'No se pudo cargar el resumen de cuentas abiertas'
    }
  } finally {
    cargando.value = false
  }
}

const cambiarCuentaSeleccionada = (event) => {
  cuentaSeleccionadaId.value = event.target.value
}

const limpiarFiltros = () => {
  fechaDesde.value = ''
  fechaHasta.value = ''
  cargarResumen()
}

const abrirModalPago = () => {
  errorPago.value = ''
  pagoForm.value = {
    monto: '',
    metodo_pago: 'transferencia',
    fecha_pago: formatDateInputValue(),
    referencia: '',
    observaciones: '',
  }
  modalPagoAbierto.value = true
}

const cerrarModalPago = () => {
  modalPagoAbierto.value = false
  errorPago.value = ''
}

const abrirModalHistorial = () => {
  pagoExpandidoId.value = null
  modalHistorialAbierto.value = true
}

const cerrarModalHistorial = () => {
  modalHistorialAbierto.value = false
  pagoExpandidoId.value = null
}

const togglePagoExpandido = (pagoId) => {
  pagoExpandidoId.value = pagoExpandidoId.value === pagoId ? null : pagoId
}

const detallePagoVisible = (pagoId) => pagoExpandidoId.value === pagoId

const ventaPorId = computed(() => {
  const map = {}
  for (const venta of cuentaSeleccionada.value?.ventas || []) {
    map[venta.id] = venta
  }
  return map
})

const estadoImputacion = (imputacion) => {
  return Number(imputacion?.saldo_posterior || 0) === 0 ? 'Pago total' : 'Pago parcial'
}

const registrarPago = async () => {
  if (!cuentaSeleccionada.value) {
    return
  }

  registrandoPago.value = true
  errorPago.value = ''

  try {
    const payload = {
      cuenta_abierta_id: cuentaSeleccionada.value.cuenta_id,
      monto: pagoForm.value.monto,
      metodo_pago: pagoForm.value.metodo_pago,
      referencia: pagoForm.value.referencia || '',
      observaciones: pagoForm.value.observaciones || '',
    }

    if (pagoForm.value.fecha_pago) {
      payload.fecha_pago = toApiDateTime(pagoForm.value.fecha_pago)
    }

    await axios.post('http://localhost:8000/api/cuentas-abiertas-pagos/', payload)
    await cargarResumen()
    cerrarModalPago()
  } catch (err) {
    const apiError = err?.response?.data
    if (typeof apiError === 'string') {
      errorPago.value = apiError
    } else if (apiError?.monto?.[0]) {
      errorPago.value = apiError.monto[0]
    } else if (apiError?.non_field_errors?.[0]) {
      errorPago.value = apiError.non_field_errors[0]
    } else if (apiError?.detail) {
      errorPago.value = apiError.detail
    } else {
      errorPago.value = 'No se pudo registrar el pago'
    }
  } finally {
    registrandoPago.value = false
  }
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
        <p>Acá podes ver un resumen de cada cuenta abierta, registrar pagos y exportar la información</p>
      </div>

      <div class="filters-actions">
        <label class="cuenta-selector">
          Cuenta
          <select :value="cuentaSeleccionadaId" @change="cambiarCuentaSeleccionada">
            <option value="" disabled>Seleccioná una cuenta</option>
            <option v-for="opcion in opcionesCuentas" :key="opcion.value" :value="opcion.value">
              {{ opcion.label }}
            </option>
          </select>
        </label>

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

    <section v-else class="cuenta-display">
      <div v-if="cuentas.length === 0" class="estado-msg">No hay cuentas abiertas para mostrar.</div>

      <div v-else-if="!cuentaSeleccionada" class="estado-msg">Seleccioná una cuenta para ver su detalle.</div>

      <article v-else :key="cuentaSeleccionada.cuenta_id" class="cuenta-card">
        <header class="cuenta-header">
          <div>
            <h3>{{ cuentaSeleccionada.nombre_departamento }}</h3>
            <p v-if="cuentaSeleccionada.responsable">Responsable: {{ cuentaSeleccionada.responsable }}</p>
          </div>

          <div class="cuenta-resumen">
            <div class="cuenta-metricas">
              <strong>{{ formatMoney(cuentaSeleccionada.total_pendiente) }}</strong>
              <small>{{ cuentaSeleccionada.cantidad_ventas }} ventas | Pagado: {{ formatMoney(cuentaSeleccionada.total_pagado) }}</small>
            </div>

            <div class="cuenta-actions">
              <button
                type="button"
                class="btn-secondary"
                :disabled="(cuentaSeleccionada.pagos || []).length === 0"
                @click="abrirModalHistorial"
              >
                Historial de pagos
              </button>

              <button
                type="button"
                class="btn-primary"
                :disabled="Number(cuentaSeleccionada.total_pendiente || 0) <= 0"
                @click="abrirModalPago"
              >
                Registrar pago
              </button>
              <button
                type="button"
                class="btn-export"
                :disabled="estaExportando(cuentaSeleccionada.cuenta_id, 'excel')"
                @click="exportarExcelCuenta(cuentaSeleccionada)"
              >
                {{ estaExportando(cuentaSeleccionada.cuenta_id, 'excel') ? 'Generando...' : 'Exportar Excel' }}
              </button>
              <button
                type="button"
                class="btn-export"
                :disabled="estaExportando(cuentaSeleccionada.cuenta_id, 'pdf')"
                @click="exportarPdfCuenta(cuentaSeleccionada)"
              >
                {{ estaExportando(cuentaSeleccionada.cuenta_id, 'pdf') ? 'Generando...' : 'Exportar PDF' }}
              </button>
            </div>
          </div>
        </header>

        <div v-if="(cuentaSeleccionada.ventas || []).length === 0" class="estado-msg">
          No hay ventas para esta cuenta en el rango seleccionado.
        </div>

        <table v-else class="ventas-table">
          <thead>
            <tr>
              <th>Fecha</th>
              <th>Becado</th>
              <th class="right">Total</th>
              <th class="right">Saldo</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="venta in ventasVisibles(cuentaSeleccionada)" :key="venta.id">
              <td>{{ formatDateTime(venta.fecha) }}</td>
              <td>{{ venta.becado_nombre }}</td>
              <td class="right">{{ formatMoney(venta.total) }}</td>
              <td class="right">{{ formatMoney(venta.saldo) }}</td>
            </tr>
          </tbody>
        </table>

        <div v-if="puedeExpandir(cuentaSeleccionada)" class="cuenta-footer">
          <button type="button" class="btn-link" @click="toggleCuentaExpandida(cuentaSeleccionada.cuenta_id)">
            {{ cuentaExpandida(cuentaSeleccionada.cuenta_id) ? 'Ver menos' : 'Ver mas' }}
          </button>
        </div>
      </article>
    </section>

    <div v-if="modalPagoAbierto" class="modal-overlay" @click.self="cerrarModalPago">
      <section class="modal-card">
        <header>
          <h3>Registrar pago</h3>
          <p>{{ cuentaSeleccionada?.nombre_departamento }}</p>
        </header>

        <div class="form-grid">
          <label>
            Monto
            <input v-model="pagoForm.monto" type="number" min="0.01" step="0.01" />
          </label>

          <label>
            Metodo
            <select v-model="pagoForm.metodo_pago">
              <option value="efectivo">Efectivo</option>
              <option value="transferencia">Transferencia</option>
              <option value="otro">Otro</option>
            </select>
          </label>

          <label>
            Fecha de pago
            <input v-model="pagoForm.fecha_pago" type="datetime-local" />
          </label>

          <label>
            Referencia
            <input v-model="pagoForm.referencia" type="text" maxlength="100" />
          </label>

          <label class="full-width">
            Observaciones
            <textarea v-model="pagoForm.observaciones" rows="3" />
          </label>
        </div>

        <p v-if="errorPago" class="estado-msg error">{{ errorPago }}</p>

        <footer class="modal-actions">
          <button type="button" class="btn-secondary" @click="cerrarModalPago">Cancelar</button>
          <button type="button" class="btn-primary" :disabled="registrandoPago" @click="registrarPago">
            {{ registrandoPago ? 'Guardando...' : 'Confirmar pago' }}
          </button>
        </footer>
      </section>
    </div>

    <div v-if="modalHistorialAbierto" class="modal-overlay" @click.self="cerrarModalHistorial">
      <section class="modal-card historial-modal">
        <header>
          <h3>Historial de pagos</h3>
          <p>{{ cuentaSeleccionada?.nombre_departamento }}</p>
        </header>

        <div v-if="(cuentaSeleccionada?.pagos || []).length === 0" class="estado-msg">
          No hay pagos registrados para esta cuenta.
        </div>

        <div v-else class="pagos-historial-list">
          <article v-for="pago in cuentaSeleccionada.pagos" :key="pago.id" class="pago-card">
            <div class="pago-card-header">
              <div>
                <strong>{{ formatMoney(pago.monto) }}</strong>
                <p>{{ formatDateTime(pago.fecha_pago) }} | {{ formatTipoPago(pago.metodo_pago) }}</p>
              </div>
              <button type="button" class="btn-link" @click="togglePagoExpandido(pago.id)">
                {{ detallePagoVisible(pago.id) ? 'Ocultar detalles' : 'Ver detalles' }}
              </button>
            </div>

            <div v-if="detallePagoVisible(pago.id)" class="imputaciones-wrap">
              <table class="ventas-table">
                <thead>
                  <tr>
                    <th>Venta</th>
                    <th>Fecha venta</th>
                    <th class="right">Monto aplicado</th>
                    <th class="right">Saldo posterior</th>
                    <th>Estado</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="imputacion in pago.imputaciones || []" :key="`${pago.id}-${imputacion.venta_id}`">
                    <td>#{{ imputacion.venta_id }}</td>
                    <td>{{ formatDateTime(ventaPorId[imputacion.venta_id]?.fecha) }}</td>
                    <td class="right">{{ formatMoney(imputacion.monto_aplicado) }}</td>
                    <td class="right">{{ formatMoney(imputacion.saldo_posterior) }}</td>
                    <td>
                      <span
                        class="estado-pill"
                        :class="Number(imputacion.saldo_posterior || 0) === 0 ? 'total' : 'parcial'"
                      >
                        {{ estadoImputacion(imputacion) }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </article>
        </div>

        <footer class="modal-actions">
          <button type="button" class="btn-secondary" @click="cerrarModalHistorial">Cerrar</button>
        </footer>
      </section>
    </div>
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

.cuenta-selector {
  min-width: 260px;
}

.filters-actions label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.filters-actions input {
  width: 100%;
}

.filters-actions input,
.filters-actions select {
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

.btn-primary {
  border: 0;
  border-radius: 10px;
  padding: 9px 14px;
  font-weight: 700;
  cursor: pointer;
  background: #0f766e;
  color: #ffffff;
}

.btn-primary:hover {
  background: #0d6a63;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.cuenta-display {
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

.cuenta-resumen {
  display: grid;
  gap: 8px;
  justify-items: end;
}

.cuenta-metricas strong {
  color: #0578af;
  font-size: 18px;
}

.cuenta-metricas small {
  color: #64748b;
}

.cuenta-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-export {
  border: 1px solid #d8dde6;
  border-radius: 10px;
  padding: 8px 10px;
  background: #ffffff;
  color: #0f172a;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 20;
}

.modal-card {
  width: min(680px, 100%);
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #d8dde6;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.modal-card h3 {
  margin: 0;
  color: #0f172a;
}

.modal-card p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-grid label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.form-grid input,
.form-grid select,
.form-grid textarea {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 10px;
  color: #0f172a;
  font: inherit;
}

.full-width {
  grid-column: 1 / -1;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.historial-modal {
  width: min(900px, 100%);
}

.pagos-historial-list {
  display: grid;
  gap: 10px;
  max-height: 55vh;
  overflow-y: auto;
  padding-right: 4px;
}

.pago-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 10px;
  display: grid;
  gap: 8px;
}

.pago-card-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
}

.pago-card-header p {
  margin: 4px 0 0;
}

.imputaciones-wrap {
  border-top: 1px solid #f1f5f9;
  padding-top: 8px;
}

.estado-pill {
  display: inline-flex;
  border-radius: 999px;
  padding: 3px 8px;
  font-size: 11px;
  font-weight: 700;
}

.estado-pill.total {
  background: #dcfce7;
  color: #166534;
}

.estado-pill.parcial {
  background: #fef3c7;
  color: #92400e;
}

.btn-export:hover {
  background: #f8fafc;
}

.btn-export:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

  .cuenta-resumen {
    justify-items: start;
  }

  .ventas-table {
    display: block;
    overflow-x: auto;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
