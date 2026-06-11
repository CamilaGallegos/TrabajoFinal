<script setup>
import axios from 'axios'
import { computed, onMounted, ref } from 'vue'
import LoginCard from './components/LoginCard.vue'
import QuickServicesPanel from './components/QuickServicesPanel.vue'
import TicketPanel from './components/TicketPanel.vue'
import { useAuth } from './composables/useAuth'
import { useCatalogo } from './composables/useCatalogo'
import { useCarrito } from './composables/useCarrito'
import { usePago } from './composables/usePago'

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
  isAuthenticated,
  becadosActivos,
  sesionActivaId,
  becadoActual,
  errorMensaje,
  infoMensaje,
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
  },
})

const vistaVentas = ref('panel')
const ventasRecientes = ref([])
const cargandoVentas = ref(false)
const errorVentas = ref('')

const ventasOrdenadas = computed(() => [...ventasRecientes.value])

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

  return 'No se pudo registrar la venta, revisa los datos e intenta nuevamente.'
}

const confirmarVenta = async () => {
  if (!validarPrevioConfirmacion()) {
    return
  }

  const payloadVenta = construirPayloadVenta()

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

onMounted(async () => {
  await restaurarSesion()
  if (isAuthenticated.value) {
    await obtenerVentas()
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
  vistaVentas.value = 'panel'
}

const irAlHistorial = async () => {
  vistaVentas.value = 'historial'
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
      :error-mensaje="errorMensaje"
      @update:dni-input="dniInput = $event"
      @iniciar-sesion="iniciarSesion"
    />

    <div v-else>
      <header class="app-header">
        <div class="app-header__brand">
          <span class="app-header__title">SiGFo CURZAS</span>
          <span class="app-header__subtitle">Sistema de Gestión de la Fotocopiadora del CURZAS</span>
        </div>

        <div class="app-header__center">
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
          <strong v-if="becadoActual" class="app-header__value">Sesión operativa: {{ becadoActual.nombre }}</strong>
          <small class="success-text">{{ infoMensaje }}</small>
        </div>

        <div class="app-header__actions">
          <div class="header-login-add">
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
          <button @click="cerrarSesion" class="btn-danger">Cerrar Sesión Actual</button>
          <button @click="cerrarTodasLasSesiones" class="btn-danger btn-danger--secondary">Cerrar Todas</button>
        </div>
      </header>

      <p v-if="errorMensaje" class="header-error">{{ errorMensaje }}</p>

      <h1 class="title">Panel de Ventas</h1>

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

        <p v-if="cargandoVentas" class="historial-empty">Cargando ventas...</p>
        <p v-else-if="errorVentas" class="historial-error">{{ errorVentas }}</p>
        <p v-else-if="ventasOrdenadas.length === 0" class="historial-empty">Todavia no hay ventas registradas</p>

        <div v-else class="historial-lista">
          <article v-for="venta in ventasOrdenadas" :key="venta.id" class="historial-item">
            <div class="historial-item__top">
              <strong>#{{ venta.id }}</strong>
              <span>{{ formatearFechaVenta(venta.fecha) }}</span>
            </div>
            <div class="historial-item__body">
              <span>Becado/a: {{ venta.becado_nombre || 'Sin nombre' }}</span>
              <span>Pago: {{ venta.tipo_pago }}</span>
              <span>Total: ${{ Number(venta.total).toFixed(2) }}</span>
            </div>
            <ul class="historial-detalles">
              <li v-for="detalle in venta.detalles" :key="`${venta.id}-${detalle.producto_id}`">
                {{ detalle.producto_nombre }} x {{ detalle.cantidad }}
              </li>
            </ul>
          </article>
        </div>
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

.historial-panel__header h2 {
  margin: 0;
  font-size: 20px;
  color: #08324a;
}

.historial-panel__header p {
  margin: 4px 0 0;
  color: #5b6b79;
}

.historial-lista {
  display: grid;
  gap: 12px;
}

.historial-item {
  border: 1px solid #e3e8ee;
  border-radius: 12px;
  padding: 14px;
  background: #fdfefe;
}

.historial-item__top,
.historial-item__body {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.historial-item__top {
  margin-bottom: 8px;
  color: #08324a;
}

.historial-item__body {
  font-size: 14px;
  color: #334155;
  margin-bottom: 8px;
}

.historial-detalles {
  margin: 0;
  padding-left: 18px;
  color: #506070;
  font-size: 13px;
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
