<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'

const auditorias = ref([])
const cargandoAuditorias = ref(false)
const errorAuditorias = ref('')
const feedback = ref({ show: false, message: '', type: 'success' })
const ventaFilter = ref('')
const auditDrawer = ref(null)
const productosPorId = ref({})
const cuentasAbiertasPorId = ref({})
let auditoriasIntervalId = null

const mostrarFeedback = (message, type = 'success') => {
  feedback.value = { show: true, message, type }
  window.clearTimeout(mostrarFeedback.timeout)
  mostrarFeedback.timeout = window.setTimeout(() => {
    feedback.value.show = false
  }, 2500)
}

const normalizarFechaAuditoria = (fecha) => {
  if (!fecha) return ''
  const d = new Date(fecha)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}:${String(d.getSeconds()).padStart(2, '0')}`
}

const agruparAuditorias = (lista) => {
  return lista.map((item) => {
    const grupo = { ...item, cambios: [item] }
    const cambiosExpandidoAnterior = grupo.cambios.flatMap((item) => expandirCambioAuditoria(item, 'valor_anterior'))
    const cambiosExpandidoNuevo = grupo.cambios.flatMap((item) => expandirCambioAuditoria(item, 'valor_nuevo'))
    const campos = [...new Set(cambiosExpandidoNuevo.map((item) => item.campo).filter(Boolean))]
    const valorAnterior = cambiosExpandidoAnterior
      .map((item) => `${item.campo}=${item.valor}`)
      .join(' | ')
    const valorNuevo = cambiosExpandidoNuevo
      .map((item) => `${item.campo}=${item.valor}`)
      .join(' | ')

    return {
      ...grupo,
      campo_modificado: campos.length > 1 ? 'Varios campos' : campos[0] || 'Cambio',
      valor_anterior: valorAnterior,
      valor_nuevo: valorNuevo,
      cantidadCambios: grupo.cambios.length,
    }
  })
}

const auditoriasAgrupadas = computed(() => agruparAuditorias(auditorias.value))

const auditiasFiltradas = computed(() => {
  const lista = auditoriasAgrupadas.value
  if (!ventaFilter.value) return lista
  return lista.filter((a) => String(a.venta_id) === ventaFilter.value)
})

const formatearFechaAuditoria = (fecha) => {
  const d = new Date(fecha)
  return d.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const formatearCampoAuditoria = (campo) => {
  const labels = {
    detalles: 'Detalles',
    total: 'Total',
    monto_efectivo: 'Monto en efectivo',
    monto_transferencia: 'Monto por transferencia',
    tipo_pago: 'Tipo de pago',
    cuenta_abierta: 'Cuenta abierta',
  }
  return labels[campo] || campo || 'Cambio'
}

const formatearMontoAuditoria = (valor) => {
  const numero = Number(valor)
  if (Number.isNaN(numero)) {
    return String(valor || 'Sin información')
  }

  return `$${numero.toLocaleString('es-AR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

const formatearTipoPagoAuditoria = (valor) => {
  const labels = {
    efectivo: 'Efectivo',
    transferencia: 'Transferencia',
    combinado: 'Combinado',
    cuenta_abierta: 'Cuenta abierta',
  }

  return labels[String(valor || '').trim()] || String(valor || 'Sin información')
}

const formatearCuentaAbiertaAuditoria = (valor) => {
  const texto = String(valor || '').trim()
  if (!texto) {
    return 'Sin cuenta abierta'
  }

  if (/^\d+$/.test(texto)) {
    return cuentasAbiertasPorId.value[texto] || `Cuenta #${texto}`
  }

  return texto
}

const resolverNombreProducto = (valor) => {
  const texto = String(valor || '').trim()
  if (!texto) return 'Producto'

  if (/^\d+$/.test(texto)) {
    return productosPorId.value[texto] || `Producto ${texto}`
  }

  return texto
}

const formatearDetalleAuditoria = (rawValor) => {
  const partes = String(rawValor || '').split(':')
  if (partes.length !== 3) {
    return String(rawValor || 'Sin información')
  }

  const [productoRef, cantidad, precioUnitario] = partes
  const productoNombre = resolverNombreProducto(productoRef)
  return `${productoNombre} x ${cantidad} · ${formatearMontoAuditoria(precioUnitario)}`
}

const parsearPartesAuditoria = (valor) => {
  const texto = String(valor || '').trim()
  if (!texto) {
    return []
  }

  return texto
    .split(' | ')
    .map((parte) => parte.trim())
    .filter(Boolean)
}

const normalizarCampoValor = (parte) => {
  const indice = parte.indexOf('=')
  if (indice === -1) {
    return { campo: '', valor: parte }
  }

  return {
    campo: parte.slice(0, indice).trim(),
    valor: parte.slice(indice + 1).trim(),
  }
}

const expandirCambioAuditoria = (item, lado) => {
  const valor = item?.[lado]
  const campo = String(item?.campo_modificado || '').trim()

  if (!campo) {
    return []
  }

  if (campo !== 'Varios campos') {
    return [{ campo, valor: String(valor || '') }]
  }

  const partes = parsearPartesAuditoria(valor)
  if (partes.length === 0) {
    return []
  }

  return partes.map((parte) => {
    const normalizado = normalizarCampoValor(parte)
    return {
      campo: normalizado.campo || campo,
      valor: normalizado.valor,
    }
  })
}

const formatearValorCampoAuditoria = (campo, valor) => {
  const texto = String(valor || '').trim()
  if (!texto) {
    return 'Sin información'
  }

  if (campo === 'detalles') {
    return texto
      .split('|')
      .map((parte) => parte.trim())
      .filter(Boolean)
      .map((parte) => formatearDetalleAuditoria(parte))
      .join('\n')
  }

  if (['total', 'monto_efectivo', 'monto_transferencia'].includes(campo)) {
    return formatearMontoAuditoria(texto)
  }

  if (campo === 'tipo_pago') {
    return formatearTipoPagoAuditoria(texto)
  }

  if (campo === 'cuenta_abierta') {
    return formatearCuentaAbiertaAuditoria(texto)
  }

  return texto
}

const construirFilasCambioAuditoria = (auditoria) => {
  if (!auditoria) {
    return []
  }

  const anteriores = new Map()
  const nuevos = new Map()
  const ordenCampos = []

  const registrarCampo = (campo) => {
    if (campo && !ordenCampos.includes(campo)) {
      ordenCampos.push(campo)
    }
  }

  for (const parte of parsearPartesAuditoria(auditoria.valor_anterior)) {
    const { campo, valor } = normalizarCampoValor(parte)
    const campoNormalizado = campo || auditoria.campo_modificado
    registrarCampo(campoNormalizado)
    anteriores.set(campoNormalizado, valor)
  }

  for (const parte of parsearPartesAuditoria(auditoria.valor_nuevo)) {
    const { campo, valor } = normalizarCampoValor(parte)
    const campoNormalizado = campo || auditoria.campo_modificado
    registrarCampo(campoNormalizado)
    nuevos.set(campoNormalizado, valor)
  }

  if (ordenCampos.length === 0) {
    const campo = auditoria.campo_modificado || 'Cambio'
    return [{
      campo,
      etiqueta: formatearCampoAuditoria(campo),
      valorAnterior: formatearValorCampoAuditoria(campo, auditoria.valor_anterior),
      valorNuevo: formatearValorCampoAuditoria(campo, auditoria.valor_nuevo),
    }]
  }

  return ordenCampos.map((campo) => ({
    campo,
    etiqueta: formatearCampoAuditoria(campo),
    valorAnterior: formatearValorCampoAuditoria(campo, anteriores.get(campo)),
    valorNuevo: formatearValorCampoAuditoria(campo, nuevos.get(campo)),
  }))
}

const filasCambioDrawer = computed(() => construirFilasCambioAuditoria(auditDrawer.value))

const obtenerProductosAuditoria = async () => {
  try {
    const respuesta = await axios.get('http://localhost:8000/api/productos/')
    const productos = Array.isArray(respuesta.data) ? respuesta.data : []
    productosPorId.value = productos.reduce((acc, producto) => {
      acc[String(producto.id)] = producto.nombre
      return acc
    }, {})
  } catch (error) {
    productosPorId.value = {}
  }
}

const obtenerCuentasAbiertasAuditoria = async () => {
  try {
    const respuesta = await axios.get('http://localhost:8000/api/cuentas-abiertas/', {
      params: { incluye_inactivas: true },
    })
    const cuentas = Array.isArray(respuesta.data) ? respuesta.data : []
    cuentasAbiertasPorId.value = cuentas.reduce((acc, cuenta) => {
      acc[String(cuenta.id)] = cuenta.nombre_departamento
      return acc
    }, {})
  } catch (error) {
    cuentasAbiertasPorId.value = {}
  }
}

const obtenerAuditorias = async () => {
  cargandoAuditorias.value = true
  errorAuditorias.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/auditorias/', {
      params: { _: Date.now() },
    })
    auditorias.value = Array.isArray(respuesta.data) ? respuesta.data : []
  } catch (error) {
    auditorias.value = []
    if (error.response?.status === 401) {
      errorAuditorias.value = 'Tu sesión no está autorizada para consultar auditorías. Vuelve a iniciar sesión.'
    } else {
      errorAuditorias.value = 'No se pudo cargar el registro de auditorías'
    }
  } finally {
    cargandoAuditorias.value = false
  }
}

const refrescarAuditorias = async () => {
  await Promise.all([obtenerProductosAuditoria(), obtenerCuentasAbiertasAuditoria(), obtenerAuditorias()])
}

const manejarCambioVisibilidad = () => {
  if (document.visibilityState === 'visible') {
    refrescarAuditorias()
  }
}

const iniciarAutoRefresh = () => {
  if (auditoriasIntervalId) {
    window.clearInterval(auditoriasIntervalId)
  }
  auditoriasIntervalId = window.setInterval(() => {
    refrescarAuditorias()
  }, 10000)
}

const detenerAutoRefresh = () => {
  if (!auditoriasIntervalId) {
    return
  }
  window.clearInterval(auditoriasIntervalId)
  auditoriasIntervalId = null
}

const abrirDetalles = (auditoria) => {
  auditDrawer.value = auditoria
}

const cerrarDrawer = () => {
  auditDrawer.value = null
}

onMounted(() => {
  refrescarAuditorias()
  iniciarAutoRefresh()
  document.addEventListener('visibilitychange', manejarCambioVisibilidad)
})

onBeforeUnmount(() => {
  detenerAutoRefresh()
  document.removeEventListener('visibilitychange', manejarCambioVisibilidad)
})
</script>

<template>
  <div class="audit-container">
    <header class="audit-header">
      <div>
        <h1>Auditoría de cambios</h1>
        <p>Registro de todas las ediciones realizadas en las ventas del sistema</p>
      </div>
      <button type="button" class="btn-refresh" @click="refrescarAuditorias">
        Actualizar
      </button>
    </header>

    <div v-if="feedback.show" class="feedback-banner" :class="feedback.type">
      {{ feedback.message }}
    </div>

    <section class="audit-filters-card">
      <div class="filtro-item filtro-buscar">
        <label for="ventaFilter">Filtrar por ID de venta</label>
        <input
          id="ventaFilter"
          v-model="ventaFilter"
          type="text"
          placeholder="Ej: 123"
        />
      </div>
    </section>

    <section class="audit-table-card">
      <div v-if="cargandoAuditorias" class="audit-loading">Cargando auditorías...</div>
      <div v-else-if="errorAuditorias" class="audit-error">{{ errorAuditorias }}</div>
      <div v-else-if="auditiasFiltradas.length === 0" class="audit-empty">
        No se encontraron cambios registrados
      </div>
      <table v-else class="audit-table">
        <thead>
          <tr>
            <th>Venta</th>
            <th>Becado/a</th>
            <th>Usuario</th>
            <th>Fecha</th>
            <th>Campo</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="auditoria in auditiasFiltradas" :key="auditoria.id" class="audit-row">
            <td class="col-venta">#{{ auditoria.venta_id }}</td>
            <td class="col-becado">{{ auditoria.becado_nombre || 'Sin nombre' }}</td>
            <td class="col-usuario">{{ auditoria.usuario_nombre || 'N/A' }}</td>
            <td class="col-fecha">{{ formatearFechaAuditoria(auditoria.fecha_correccion) }}</td>
            <td class="col-campo">{{ auditoria.campo_modificado }}</td>
            <td class="col-acciones">
              <button type="button" class="btn-audit btn-detalles" @click="abrirDetalles(auditoria)">
                Ver cambio
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <Teleport to="body">
      <div v-if="auditDrawer" class="drawer-overlay" @click.self="cerrarDrawer">
        <aside class="drawer">
          <div class="drawer__header">
            <h3>Cambio en Venta #{{ auditDrawer.venta_id }}</h3>
            <button type="button" class="drawer__close" @click="cerrarDrawer">✕</button>
          </div>

          <div class="drawer__body">
            <dl class="drawer-info">
              <dt>Becado/a</dt>
              <dd>{{ auditDrawer.becado_nombre || 'Sin nombre' }}</dd>
              <dt>Usuario que editó</dt>
              <dd>{{ auditDrawer.usuario_nombre || 'N/A' }}</dd>
              <dt>Fecha de edición</dt>
              <dd>{{ formatearFechaAuditoria(auditDrawer.fecha_correccion) }}</dd>
            </dl>

            <section class="cambio-detalle-card">
              <header class="cambio-detalle-header">
                <h4>Cambios</h4>
              </header>

              <div class="cambio-grid-header">
                <span>Campo</span>
                <span>Antes</span>
                <span>Después</span>
              </div>

              <div v-for="fila in filasCambioDrawer" :key="`${auditDrawer.id}-${fila.campo}`" class="cambio-grid-row">
                <div class="campo-pill">{{ fila.etiqueta }}</div>
                <pre class="valor-box valor-box--anterior">{{ fila.valorAnterior }}</pre>
                <pre class="valor-box valor-box--nuevo">{{ fila.valorNuevo }}</pre>
              </div>
            </section>

            <div v-if="auditDrawer.motivo" class="motivo-seccion">
              <h4>Motivo de la corrección</h4>
              <p class="motivo-texto">{{ auditDrawer.motivo }}</p>
            </div>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.audit-container {
  width: 100%;
  display: grid;
  gap: 20px;
}

.audit-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border: 1px solid #d8dde6;
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f3f9fc 100%);
}

.btn-refresh {
  border: 0;
  border-radius: 10px;
  padding: 10px 14px;
  background: #0578af;
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
}

.btn-refresh:hover {
  background: #046892;
}

.audit-header h1 {
  margin: 0 0 6px;
  color: #08324a;
}

.audit-header p {
  margin: 0;
  color: #5b6b79;
  max-width: none;
  width: 100%;
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

.audit-filters-card {
  background: #ffffff;
  border: 1px solid #d8dde6;
  border-radius: 16px;
  padding: 16px;
}

.filtro-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  max-width: 300px;
}

.filtro-item label {
  font-size: 11px;
  color: #475569;
  text-transform: uppercase;
  font-weight: 600;
}

.filtro-item input {
  padding: 8px 10px;
  border: 1px solid #d8dde6;
  border-radius: 8px;
  font-size: 13px;
  background: #ffffff;
}

.filtro-item input:focus {
  outline: none;
  border-color: #0578af;
  box-shadow: 0 0 0 3px rgba(5, 120, 175, 0.1);
}

.audit-table-card {
  width: 100%;
  background: #ffffff;
  border: 1px solid #d8dee7;
  border-radius: 16px;
  overflow: hidden;
}

.audit-loading,
.audit-error,
.audit-empty {
  padding: 28px;
  color: #475569;
  text-align: center;
  font-size: 14px;
}

.audit-error {
  color: #dc2626;
}

.audit-table {
  width: 100%;
  border-collapse: collapse;
}

.audit-row {
  border-bottom: 1px solid #eef2f7;
}

.audit-row:last-child {
  border-bottom: none;
}

.audit-row td {
  padding: 12px 14px;
  font-size: 13px;
  color: #475569;
}

.col-venta {
  color: #0578af;
  font-weight: 600;
  min-width: 60px;
}

.col-usuario {
  min-width: 120px;
}

.col-fecha {
  color: #64748b;
  font-size: 12px;
  min-width: 160px;
}

.col-campo {
  font-weight: 600;
  color: #0f172a;
  min-width: 120px;
}

.col-acciones {
  text-align: right;
  min-width: 120px;
}

.btn-audit {
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

.btn-audit:hover {
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
  grid-template-columns: 120px 1fr;
  gap: 12px 16px;
  margin-bottom: 24px;
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

.campo-destaque {
  background: #f1f8ff;
  padding: 4px 8px;
  border-radius: 4px;
  font-weight: 600;
  color: #0578af;
}

.cambio-detalle-card {
  margin-bottom: 20px;
  padding: 16px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.cambio-detalle-header {
  margin-bottom: 14px;
}

.cambio-detalle-header h4 {
  margin: 0 0 4px;
  font-size: 14px;
  color: #0f172a;
}

.cambio-detalle-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.cambio-grid-header,
.cambio-grid-row {
  display: grid;
  grid-template-columns: 140px 1fr 1fr;
  gap: 12px;
  align-items: start;
}

.cambio-grid-header {
  padding: 0 0 10px;
  border-bottom: 1px solid #dbe4ee;
  margin-bottom: 12px;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  color: #64748b;
}

.cambio-grid-row {
  padding: 12px 0;
  border-bottom: 1px solid #e7edf4;
}

.cambio-grid-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.campo-pill {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #eaf4fb;
  color: #055a82;
  font-size: 12px;
  font-weight: 700;
}

.valor-box {
  margin: 0;
  padding: 10px 12px;
  background: #ffffff;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  color: #0f172a;
  line-height: 1.5;
}

.valor-box--anterior {
  border-left: 4px solid #fca5a5;
  background: #fff7f7;
}

.valor-box--nuevo {
  border-left: 4px solid #86efac;
  background: #f4fff7;
}

.motivo-seccion {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid #e2e8f0;
}

.motivo-seccion h4 {
  margin: 0 0 12px;
  font-size: 13px;
  text-transform: uppercase;
  color: #64748b;
  font-weight: 600;
}

.motivo-texto {
  margin: 0;
  padding: 12px;
  background: #f9fafb;
  border-radius: 8px;
  border-left: 4px solid #0578af;
  font-size: 13px;
  color: #0f172a;
  line-height: 1.6;
}

@media (max-width: 760px) {
  .cambio-grid-header {
    display: none;
  }

  .cambio-grid-row {
    grid-template-columns: 1fr;
  }

  .drawer {
    width: 100vw;
  }
}
</style>
