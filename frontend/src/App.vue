<script setup>
import { onMounted } from 'vue'
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
  await Promise.all([obtenerProductos(), obtenerCuentasAbiertas()])
}

const {
  dniInput,
  isAuthenticated,
  becadoActual,
  errorMensaje,
  infoMensaje,
  iniciarSesion,
  cerrarSesion,
  restaurarSesion,
} = useAuth({
  onLoginSuccess: cargarDatosSesion,
  onLogout: () => {
    resetCatalogo()
    resetCarrito()
    resetPago()
  },
})

const agregarLibreriaDesdeBusqueda = (producto) => {
  agregarAlCarrito(producto)
  busquedaLibreria.value = ''
}

const confirmarVenta = () => {
  if (!validarPrevioConfirmacion()) {
    return
  }

  const payloadVenta = construirPayloadVenta()
  console.log('Venta lista para enviar:', payloadVenta)

  infoMensaje.value = 'Venta preparada correctamente. Falta conectar el endpoint para guardarla.'
  resetCarrito()
  resetPago()
}

onMounted(async () => {
  await restaurarSesion()
})
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
      <div class="topbar">
        <div>
          <span>Becado activo: <strong>{{ becadoActual.nombre }}</strong></span>
          <br />
          <small class="success-text">{{ infoMensaje }}</small>
        </div>
        <button @click="cerrarSesion" class="btn-danger">Cerrar Sesión</button>
      </div>

      <h1 class="title">Panel de Ventas</h1>

      <div class="ventas-layout">
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
  padding: 26px;
  max-width: 1280px;
  margin: 0 auto;
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

.title {
  margin: 26px 0 14px;
  font-size: 28px;
}

.topbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f3f5f8;
  padding: 12px 18px;
  border-radius: 12px;
}

.success-text {
  color: #1f7a3e;
}

.ventas-layout {
  display: grid;
  grid-template-columns: 1.15fr 1fr;
  gap: 18px;
  align-items: start;
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

  .topbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
  }
}
</style>
