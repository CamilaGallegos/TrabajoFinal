<script setup>
import axios from 'axios'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoginCard from '../components/LoginCard.vue'
import QuickServicesPanel from '../components/QuickServicesPanel.vue'
import TicketPanel from '../components/TicketPanel.vue'
import { useAuth } from '../composables/useAuth'
import { useCatalogo } from '../composables/useCatalogo'
import { useCarrito } from '../composables/useCarrito'
import { usePago } from '../composables/usePago'

const router = useRouter()
const route = useRoute()

const {
  productos,
  cuentasAbiertas,
  busquedaLibreria,
  cargandoProductos,
  bloquesServicios,
  libreriaFiltrada,
  obtenerProductos,
  obtenerCuentasAbiertas,
  resetCatalogo,
} = useCatalogo()

const {
  carrito,
  totalVenta,
  agregarAlCarrito,
  restarCantidad,
  eliminarDelCarrito,
  disminuirServicioRapido,
  agregarServicioRapido,
  actualizarCantidadServicio,
  obtenerCantidadCarrito,
  obtenerCantidadNumerica,
  servicioActivo,
  resetCarrito,
} = useCarrito({
  productos,
  cargandoProductos,
  obtenerProductos,
})

const {
  tipoPago,
  cuentaSeleccionada,
  montoEfectivo,
  montoTransferencia,
  errorPago,
  esPagoCombinado,
  esCuentaAbierta,
  diferenciaCombinado,
  pagoValido,
  resetPago,
  validarPrevioConfirmacion,
  construirPayloadVenta,
} = usePago({
  carrito,
  totalVenta,
  onCuentaAbiertaSeleccionada: () => {
    obtenerCuentasAbiertas()
  },
})

const cargarDatosSesion = async () => {
  await Promise.all([obtenerProductos(), obtenerCuentasAbiertas(), obtenerVentas()])
}

const {
  dniInput,
  passwordInput,
  requierePassword,
  loginAdmin,
  isAuthenticated,
  becadosActivos,
  sesionActivaId,
  becadoActual,
  errorMensaje,
  infoMensaje,
  esAdmin,
  iniciarSesion,
  cerrarSesion,
  cerrarTodasLasSesiones,
  seleccionarSesionActiva,
  restaurarSesion,
} = useAuth({
  onLoginSuccess: cargarDatosSesion,
  onLogout: () => {
    resetCatalogo()
    resetCarrito()
    resetPago()
    ventasRecientes.value = []
    errorVentas.value = ''
    router.push({ name: 'login' })
  },
})

const ventasRecientes = ref([])
const cargandoVentas = ref(false)
const errorVentas = ref('')
const searchTerm = ref('')
const filtroTipoPago = ref('')
const filtroBecado = ref('')
const fechaDesde = ref('')
const fechaHasta = ref('')
const ventaEnEdicionId = ref(null)
const ventaDrawer = ref(null)
const drawerModo = ref('')

const cuentasAbiertasPorId = computed(() => {
  const mapa = new Map()
  for (const cuenta of cuentasAbiertas.value) {
    mapa.set(Number(cuenta.id), cuenta.nombre_departamento)
  }
  return mapa
})

const vistaVentas = computed(() => (route.name === 'historial' ? 'historial' : 'panel'))

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

const ventasOrdenadas = computed(() => ventasFiltradas.value)

const obtenerVentas = async () => {
  cargandoVentas.value = true
  errorVentas.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/ventas/')
    ventasRecientes.value = Array.isArray(respuesta.data) ? respuesta.data : []
  } catch (error) {
    ventasRecientes.value = []
    errorVentas.value = error?.response?.status === 403
      ? 'No tenes permisos para ver el historial de ventas'
      : 'No se pudo cargar el historial de ventas'
  } finally {
    cargandoVentas.value = false
  }
}

const agregarLibreriaDesdeBusqueda = (producto) => {
  agregarAlCarrito(producto)
  busquedaLibreria.value = ''
}

const obtenerMensajeErrorVenta = (error) => {
  const data = error?.response?.data

  if (!data) {
    return 'No se pudo registrar la venta, intenta nuevamente.'
  }

  if (typeof data === 'string') {
    return data
  }

  if (Array.isArray(data)) {
    return data.join(' ')
  }

  const primerValor = Object.values(data)[0]
  if (Array.isArray(primerValor)) {
    return primerValor[0]
  }

  if (typeof primerValor === 'string') {
    return primerValor
  }

  return 'No se pudo registrar la venta, revisa los datos e intenta nuevamente'
}

const confirmarVenta = async () => {
  if (!validarPrevioConfirmacion()) {
    return
  }

  const payloadVenta = construirPayloadVenta()

  if (ventaEnEdicionId.value) {
    const motivo = window.prompt('Motivo de la correccion (auditoria):') || ''
    if (!motivo.trim()) {
      errorPago.value = 'Para editar una venta debes indicar el motivo de la correccion.'
      return
    }

    payloadVenta.motivo_auditoria = motivo.trim()

    try {
      await axios.patch(`http://localhost:8000/api/ventas/${ventaEnEdicionId.value}/`, payloadVenta)
    } catch (error) {
      errorPago.value = obtenerMensajeErrorVenta(error)
      return
    }

    infoMensaje.value = `Venta #${ventaEnEdicionId.value} actualizada correctamente.`
    ventaEnEdicionId.value = null
    await Promise.all([obtenerProductos(), obtenerVentas()])
    resetCarrito()
    resetPago()
    return
  }

  try {
    await axios.post('http://localhost:8000/api/ventas/', payloadVenta)
  } catch (error) {
    errorPago.value = obtenerMensajeErrorVenta(error)
    return
  }

  infoMensaje.value = 'Venta registrada correctamente!'
  await Promise.all([obtenerProductos(), obtenerVentas()])
  resetCarrito()
  resetPago()
}

const ventaEditable = (venta) => {
  const fechaVenta = new Date(venta.fecha).getTime()
  const ahora = Date.now()
  const limite = 24 * 60 * 60 * 1000
  return (ahora - fechaVenta) <= limite
}

const cargarVentaParaEdicion = async (venta) => {
  if (!ventaEditable(venta)) {
    return
  }

  const mapaProductos = new Map(productos.value.map((p) => [p.id, p]))
  carrito.value = venta.detalles.map((detalle) => {
    const productoCatalogo = mapaProductos.get(detalle.producto_id)
    return {
      id: detalle.producto_id,
      nombre: detalle.producto_nombre,
      precio: Number(detalle.precio_unitario),
      cantidad: detalle.cantidad,
      es_servicio: Boolean(productoCatalogo?.es_servicio),
      stock_maximo: productoCatalogo?.stock ?? null,
    }
  })

  tipoPago.value = venta.tipo_pago
  cuentaSeleccionada.value = venta.cuenta_abierta ?? ''
  montoEfectivo.value = String(venta.monto_efectivo)
  montoTransferencia.value = String(venta.monto_transferencia)
  errorPago.value = ''
  ventaEnEdicionId.value = venta.id

  await router.push({ name: 'panel' })
}

const cancelarEdicionVenta = () => {
  ventaEnEdicionId.value = null
  resetCarrito()
  resetPago()
  infoMensaje.value = 'Edicion cancelada.'
}

const abrirDetalles = (venta) => {
  ventaDrawer.value = venta
  drawerModo.value = 'detalles'
}

const abrirEditar = (venta) => {
  ventaDrawer.value = venta
  drawerModo.value = 'editar'
}

const cerrarDrawer = () => {
  ventaDrawer.value = null
  drawerModo.value = ''
}

const confirmarEdicionDesdeDrawer = async () => {
  const ventaSeleccionada = ventaDrawer.value
  cerrarDrawer()
  if (ventaSeleccionada) {
    await cargarVentaParaEdicion(ventaSeleccionada)
  }
}

const obtenerNombreCuentaAbierta = (cuentaAbiertaId) => {
  if (!cuentaAbiertaId) {
    return ''
  }

  return cuentasAbiertasPorId.value.get(Number(cuentaAbiertaId)) || `Cuenta #${cuentaAbiertaId}`
}

onMounted(async () => {
  await restaurarSesion()
  if (isAuthenticated.value && route.name === 'login') {
    router.replace({ name: 'panel' })
    await obtenerVentas()
    return
  }

  if (isAuthenticated.value) {
    await obtenerVentas()
    return
  }

  if (route.name !== 'login') {
    router.replace({ name: 'login' })
  }
})

watch(isAuthenticated, (autenticado) => {
  if (!autenticado && route.name !== 'login') {
    router.replace({ name: 'login' })
  }
})

const agregarBecadoActivo = async () => {
  await iniciarSesion()
}

const seleccionarBecado = (becadoId) => {
  seleccionarSesionActiva(String(becadoId))
}

const formatearFechaVenta = (fechaISO) => {
  return new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(new Date(fechaISO))
}

const volverAlPanel = () => {
  router.push({ name: 'panel' })
}

const irAlHistorial = async () => {
  router.push({ name: 'historial' })
  if (ventasRecientes.value.length === 0 && !cargandoVentas.value) {
    await obtenerVentas()
  }
}
</script>

<template>
  <div class="app-shell">
    <LoginCard
      v-if="!isAuthenticated"
      :dni-input="dniInput"
      :password-input="passwordInput"
      :error-mensaje="errorMensaje"
      :requires-password="requierePassword"
      :is-admin="loginAdmin"
      @update:dni-input="dniInput = $event"
      @update:password-input="passwordInput = $event"
      @iniciar-sesion="iniciarSesion"
    />

    <div v-else>
      <header class="app-header">
        <div class="app-header__brand">
          <span class="app-header__title">SiGFo CURZAS</span>
          <span class="app-header__subtitle">Sistema de Gestión de la Fotocopiadora del CURZAS</span>
        </div>

        <div class="app-header__center" v-if="!esAdmin">
          <span class="app-header__label">Becados/as activos/as: {{ becadosActivos.length }}</span>
          <div class="activos-lista">
            <button
              v-for="becado in becadosActivos"
              :key="becado.id"
              type="button"
              :class="['becado-chip', { activo: String(becado.id) === sesionActivaId }]"
              @click="seleccionarBecado(becado.id)"
            >
              {{ becado.nombre }}
            </button>
          </div>
          <strong v-if="becadoActual" class="app-header__value">Actual: {{ becadoActual.nombre }}</strong>
          <small class="success-text">{{ infoMensaje }}</small>
        </div>

        <div v-else class="app-header__center">
          <strong class="app-header__value">Panel admin</strong>
          <small class="success-text">{{ infoMensaje }}</small>
        </div>

        <div class="app-header__actions">
          <div v-if="!esAdmin" class="header-login-add">
            <input
              :value="dniInput"
              type="text"
              placeholder="DNI"
              class="header-dni-input"
              @input="dniInput = $event.target.value"
              @keyup.enter="agregarBecadoActivo"
            />
            <button type="button" class="btn-add" @click="agregarBecadoActivo">Agregar</button>
          </div>
          <button v-if="esAdmin" type="button" class="btn-add" @click="router.push({ name: 'admin-dashboard' })">
            Admin dashboard
          </button>
          <button @click="cerrarSesion" class="btn-danger">Cerrar Sesión Actual</button>
          <button @click="cerrarTodasLasSesiones" class="btn-danger btn-danger--secondary">Cerrar Todas</button>
        </div>
      </header>

      <p v-if="errorMensaje" class="header-error">{{ errorMensaje }}</p>

      <h1 class="title">Panel de Ventas</h1>

      <div v-if="ventaEnEdicionId" class="edit-banner">
        <strong>Editando venta #{{ ventaEnEdicionId }}</strong>
        <button type="button" class="btn-add" @click="cancelarEdicionVenta">Cancelar edicion</button>
      </div>

      <div class="ventas-nav">
        <button type="button" :class="['ventas-nav__btn', { activo: vistaVentas === 'panel' }]" @click="volverAlPanel">
          Registro de ventas
        </button>
        <button type="button" :class="['ventas-nav__btn', { activo: vistaVentas === 'historial' }]" @click="irAlHistorial">
          Historial de ventas
        </button>
      </div>

      <section v-if="vistaVentas === 'historial'" class="historial-panel">
        <div class="historial-panel__header">
          <div>
            <h2>Ventas recientes</h2>
          </div>
          <button type="button" class="btn-add" @click="volverAlPanel">Volver al panel</button>
        </div>

        <div class="historial-filtros">
          <div class="filtro-item filtro-buscar">
            <label for="searchTerm">Buscar</label>
            <input
              id="searchTerm"
              type="text"
              placeholder="Becada/o, producto..."
              v-model="searchTerm"
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
          <div class="filtro-item filtro-fecha">
            <label for="fechaDesde">Desde</label>
            <input id="fechaDesde" type="date" v-model="fechaDesde" />
          </div>
          <div class="filtro-item filtro-fecha">
            <label for="fechaHasta">Hasta</label>
            <input id="fechaHasta" type="date" v-model="fechaHasta" />
          </div>
        </div>

        <p v-if="cargandoVentas" class="historial-empty">Cargando ventas...</p>
        <p v-else-if="errorVentas" class="historial-error">{{ errorVentas }}</p>
        <p v-else-if="ventasOrdenadas.length === 0" class="historial-empty">No se encontraron ventas con esos filtros</p>

        <table v-else class="historial-table">
          <tbody>
            <tr
              v-for="venta in ventasOrdenadas"
              :key="venta.id"
              class="historial-row"
            >
              <td class="col-id">#{{ venta.id }}</td>
              <td class="col-fecha">{{ formatearFechaVenta(venta.fecha) }}</td>
              <td class="col-total">Total: ${{ Number(venta.total).toFixed(2) }}</td>
              <td class="col-pago">Pago: {{ venta.tipo_pago }}</td>
              <td class="col-acciones">
                <button
                  type="button"
                  class="btn-historial btn-editar"
                  :disabled="!ventaEditable(venta)"
                  :title="ventaEditable(venta) ? 'Editar venta' : 'Solo editable dentro de las 24 horas'"
                  @click="abrirEditar(venta)"
                >
                  Editar ›
                </button>
                <button
                  type="button"
                  class="btn-historial btn-detalles"
                  @click="abrirDetalles(venta)"
                >
                  Ver detalles
                </button>
              </td>
            </tr>
          </tbody>
        </table>

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
                    <dd>{{ obtenerNombreCuentaAbierta(ventaDrawer.cuenta_abierta) }}</dd>
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
                    <tr v-for="detalle in ventaDrawer.detalles" :key="detalle.producto_id">
                      <td>{{ detalle.producto_nombre }}</td>
                      <td class="right">{{ detalle.cantidad }}</td>
                      <td class="right">${{ Number(detalle.precio_unitario).toFixed(2) }}</td>
                      <td class="right">${{ (detalle.cantidad * Number(detalle.precio_unitario)).toFixed(2) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>

              <div v-if="drawerModo === 'editar'" class="drawer__footer">
                <p v-if="!ventaEditable(ventaDrawer)" class="historial-lock">
                  Esta venta ya no puede editarse (pasaron más de 24 horas).
                </p>
                <button
                  v-else
                  type="button"
                  class="btn-primary"
                  @click="confirmarEdicionDesdeDrawer"
                >
                  Editar esta venta
                </button>
              </div>
            </aside>
          </div>
        </Teleport>
      </section>

      <div v-else class="ventas-layout">
        <QuickServicesPanel
          :bloques-servicios="bloquesServicios"
          :obtener-cantidad-numerica="obtenerCantidadNumerica"
          :obtener-cantidad-carrito="obtenerCantidadCarrito"
          :servicio-activo="servicioActivo"
          :busqueda-libreria="busquedaLibreria"
          :libreria-filtrada="libreriaFiltrada"
          @disminuir-servicio="disminuirServicioRapido"
          @agregar-servicio="agregarServicioRapido"
          @actualizar-cantidad-servicio="actualizarCantidadServicio"
          @update:busqueda-libreria="busquedaLibreria = $event"
          @agregar-libreria="agregarLibreriaDesdeBusqueda"
        />

        <TicketPanel
          :carrito="carrito"
          :total-venta="totalVenta"
          :tipo-pago="tipoPago"
          :es-pago-combinado="esPagoCombinado"
          :es-cuenta-abierta="esCuentaAbierta"
          :monto-efectivo="montoEfectivo"
          :monto-transferencia="montoTransferencia"
          :pago-valido="pagoValido"
          :diferencia-combinado="diferenciaCombinado"
          :cuentas-abiertas="cuentasAbiertas"
          :cuenta-seleccionada="cuentaSeleccionada"
          :error-pago="errorPago"
          @restar-cantidad="restarCantidad"
          @agregar-al-carrito="agregarAlCarrito"
          @eliminar-del-carrito="eliminarDelCarrito"
          @update:tipo-pago="tipoPago = $event"
          @update:monto-efectivo="montoEfectivo = $event"
          @update:monto-transferencia="montoTransferencia = $event"
          @update:cuenta-seleccionada="cuentaSeleccionada = $event"
          @confirmar-venta="confirmarVenta"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
:root {
  color-scheme: light;
}

.app-shell {
  width: 100%;
  max-width: none;
  margin: 0;
  padding: clamp(12px, 1.8vw, 26px);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  color: #1f2937;
}

.btn-danger {
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  padding: 8px 14px;
  background: #c53030;
  color: #fff;
}

.btn-danger--secondary {
  background: rgba(133, 21, 21, 0.88);
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

.title {
  margin: 0;
  font-size: clamp(24px, 2.1vw, 36px);
  line-height: 1.05;
  color: #08324a;
}

.ventas-nav {
  display: flex;
  gap: 10px;
  margin: 16px 0 18px;
}

.ventas-nav__btn {
  border: 1px solid #b7cad8;
  background: #ffffff;
  color: #045b84;
  border-radius: 999px;
  padding: 9px 14px;
  font-weight: 700;
  cursor: pointer;
}

.ventas-nav__btn.activo {
  background: #0578af;
  color: #ffffff;
  border-color: #0578af;
}

.historial-panel {
  border: 1px solid #d8dde6;
  border-radius: 14px;
  background: #ffffff;
  padding: 18px;
}

.historial-panel__header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 14px;
}

.historial-filtros {
  display: grid;
  grid-template-columns: 1fr 140px 140px 120px 120px;
  gap: 8px;
  align-items: end;
  margin-bottom: 12px;
}

.filtro-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.filtro-buscar {
  grid-column: 1 / 2;
}

.filtro-fecha input {
  width: 100%;
  height: 34px;
}

.filtro-item label {
  font-size: 11px;
  color: #334155;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.filtro-item input,
.filtro-item select {
  width: 100%;
  padding: 6px 8px;
  border-radius: 8px;
  border: 1px solid #cbd5e1;
  font-size: 13px;
  height: 34px;
}

@media (max-width: 960px) {
  .historial-filtros {
    grid-template-columns: 1fr;
  }
}

.historial-panel__header h2 {
  margin: 0;
  font-size: 20px;
  color: #08324a;
}

.historial-panel__header p {
  margin: 4px 0 0;
  color: #5b6b79;
}

.historial-table {
  width: 100%;
  border-collapse: collapse;
}

.historial-row {
  background: #e8f3fb;
}

.historial-row:nth-child(odd) {
  background: #dce9f5;
}

.historial-row td {
  padding: 11px 14px;
  vertical-align: middle;
  font-size: 14px;
  color: #1a3348;
}

.col-id {
  font-weight: 700;
  width: 50px;
}

.col-fecha {
  width: 160px;
  color: #3b5268;
}

.col-total {
  font-weight: 600;
}

.col-pago {
  color: #3b5268;
}

.col-acciones {
  width: 220px;
  text-align: right;
  white-space: nowrap;
}

.btn-historial {
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1.5px solid;
}

.btn-editar {
  background: transparent;
  color: #1a7a3c;
  border-color: #1a7a3c;
  margin-right: 6px;
}

.btn-editar:disabled {
  color: #94a3b8;
  border-color: #cbd5e1;
  cursor: not-allowed;
}

.btn-detalles {
  background: transparent;
  color: #0578af;
  border-color: #0578af;
}

.drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 100;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: min(480px, 96vw);
  height: 100%;
  background: #fff;
  display: flex;
  flex-direction: column;
  box-shadow: -4px 0 24px rgba(0,0,0,0.15);
  animation: slide-in 0.2s ease;
}

@keyframes slide-in {
  from { transform: translateX(100%); }
  to   { transform: translateX(0); }
}

.drawer__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 20px;
  border-bottom: 1px solid #e2e8f0;
}

.drawer__header h3 {
  margin: 0;
  font-size: 18px;
  color: #08324a;
}

.drawer__close {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  color: #64748b;
  line-height: 1;
}

.drawer__body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.drawer__footer {
  padding: 16px 20px;
  border-top: 1px solid #e2e8f0;
}

.drawer-info {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 8px 12px;
  margin: 0 0 20px;
  font-size: 14px;
}

.drawer-info dt {
  color: #64748b;
  font-weight: 600;
}

.drawer-info dd {
  margin: 0;
  color: #1a3348;
}

.total-highlight {
  font-weight: 700;
  font-size: 16px;
  color: #1a7a3c;
}

.drawer-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.drawer-table th,
.drawer-table td {
  padding: 8px 6px;
  border-bottom: 1px solid #e8edf3;
}

.drawer-table th {
  text-align: left;
  color: #64748b;
  font-weight: 600;
}

.drawer-table .right {
  text-align: right;
}

.btn-primary {
  width: 100%;
  padding: 12px;
  background: #1a7a3c;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}

.historial-empty,
.historial-error {
  margin: 0;
  padding: 14px;
  text-align: center;
  border-radius: 10px;
}

.historial-empty {
  background: #f8fafc;
  color: #5b6b79;
}

.historial-error {
  background: #fff1f2;
  color: #b42318;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 30;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 18px;
  width: 100%;
  background: linear-gradient(90deg, #0578af 0%, #0d8bc8 55%, #0578af 100%);
  color: #ffffff;
  padding: 14px 18px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 10px 28px rgba(5, 120, 175, 0.18);
}

.app-header__brand,
.app-header__center,
.app-header__actions {
  display: flex;
  align-items: center;
}

.app-header__brand {
  flex: 1;
  flex-direction: column;
  align-items: flex-start;
  min-width: 0;
}

.app-header__title {
  font-size: clamp(20px, 1.7vw, 26px);
  font-weight: 800;
  letter-spacing: 0.4px;
  color: #ffffff;
}

.app-header__subtitle {
  font-size: 12px;
  color: rgba(255, 255, 255, 0.82);
}

.app-header__center {
  flex: 1.4;
  flex-direction: column;
  justify-content: center;
  text-align: center;
  min-width: 0;
}

.app-header__label {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: rgba(255, 255, 255, 0.8);
}

.app-header__value {
  font-size: clamp(15px, 1.15vw, 18px);
  color: #ffffff;
}

.app-header__actions {
  flex: 0 0 auto;
  justify-content: flex-end;
  gap: 8px;
}

.header-login-add {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-dni-input {
  height: 34px;
  min-width: 180px;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.55);
  padding: 0 10px;
  font-size: 13px;
  color: #08324a;
}

.header-dni-input::placeholder {
  color: #6c8091;
}

.activos-lista {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 6px;
  margin: 2px 0;
}

.becado-chip {
  border: 1px solid rgba(255, 255, 255, 0.65);
  background: rgba(255, 255, 255, 0.15);
  color: #ffffff;
  border-radius: 999px;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.becado-chip.activo {
  background: #ffffff;
  color: #045b84;
  border-color: #ffffff;
}

.success-text {
  color: #dff4ff;
}

.header-error {
  margin: 8px 2px 0;
  color: #a30d0d;
  font-size: 13px;
  font-weight: 600;
}

.edit-banner {
  margin: 12px 0;
  padding: 10px 14px;
  border: 1px solid #b7cad8;
  border-radius: 10px;
  background: #eef6ff;
  color: #08324a;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.historial-lock {
  color: #8b1c1c;
  font-size: 13px;
  margin: 0 0 10px;
}

.ventas-layout {
  display: grid;
  grid-template-columns: minmax(680px, 1.6fr) minmax(420px, 0.95fr);
  gap: clamp(16px, 1.8vw, 28px);
  align-items: start;
}

@media (min-width: 1500px) {
  .app-shell {
    padding-left: clamp(26px, 3vw, 52px);
    padding-right: clamp(26px, 3vw, 52px);
  }

  .ventas-layout {
    grid-template-columns: minmax(820px, 1.75fr) minmax(480px, 1fr);
  }
}

@media (max-width: 1080px) {
  .ventas-layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .app-shell {
    padding: 14px;
  }

  .app-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    position: static;
  }

  .app-header__center {
    align-items: flex-start;
    text-align: left;
  }

  .app-header__actions {
    width: 100%;
    flex-wrap: wrap;
    justify-content: flex-start;
  }
}
</style>
