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
      <header class="app-header">
        <div class="app-header__brand">
          <span class="app-header__title">SiGFo CURZAS</span>
          <span class="app-header__subtitle">Sistema de Gestión de la Fotocopiadora del CURZAS</span>
        </div>

        <div class="app-header__center">
          <span class="app-header__label">Becado/a activo/a: </span>
          <strong class="app-header__value">{{ becadoActual.nombre }}</strong>
          <small class="success-text">{{ infoMensaje }}</small>
        </div>

        <div class="app-header__actions">
          <button @click="cerrarSesion" class="btn-danger">Cerrar Sesión</button>
        </div>
      </header>

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

.title {
  margin: 0;
  font-size: clamp(24px, 2.1vw, 36px);
  line-height: 1.05;
  color: #08324a;
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
}

.success-text {
  color: #dff4ff;
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
}
</style>
