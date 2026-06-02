<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import axios from 'axios'

//variable para guardar los productos y fichaje
const dniInput = ref('')
const isAuthenticated = ref(false)
const token = ref('')
const becadoActual = ref(null)
const productos = ref([])
const errorMensaje = ref('')
const infoMensaje = ref('')

// estados para venta
const carrito = ref([])
const tipoPago = ref('efectivo')
const cuentaSeleccionada = ref('')
const montoEfectivo = ref('')
const montoTransferencia = ref('')
const errorPago = ref('')

// Opciones acotadas a areas institucionales validas
const cuentasAbiertas = ref([
  { id: 'dep-informatica', nombre: 'Departamento de Informatica' },
  { id: 'dep-sociales', nombre: 'Departamento de Ciencias Sociales' },
  { id: 'centro-estudiantes', nombre: 'Centro de Estudiantes' },
  { id: 'secretaria-academica', nombre: 'Secretaria Academica' },
])

const setAuthToken = (jwtToken) => {
  if (jwtToken) {
    axios.defaults.headers.common.Authorization = `Bearer ${jwtToken}`
  } else {
    delete axios.defaults.headers.common.Authorization
  }
}

const iniciarSesion = async () => {
  errorMensaje.value = ''
  infoMensaje.value = ''
  
  if (!dniInput.value) {
    errorMensaje.value = "Por favor, ingresá tu DNI"
    return
  }

  try {
    const respuesta = await axios.post('http://localhost:8000/api/fichaje/entrada/', {
      dni: dniInput.value
    })
    
    // guardamos los datos recibidos del backend
    token.value = respuesta.data.token
    becadoActual.value = respuesta.data.becado
    infoMensaje.value = respuesta.data.msg
    isAuthenticated.value = true
    setAuthToken(token.value)
    
    // Persistencia de sesion en localStorage
    localStorage.setItem('sigfo_token', token.value)
    localStorage.setItem('sigfo_becado', JSON.stringify(becadoActual.value))
    
    // Una vez logueado
    obtenerProductos()
    
  } catch (error) {
    if (error.response && error.response.status === 404) {
      errorMensaje.value = "El DNI ingresado no corresponde a un becado/a activo/a."
    } else {
      errorMensaje.value = "Error"
    }
  }
}

const obtenerProductos = async () => {
  try {
    const respuesta = await axios.get('http://localhost:8000/api/productos/')
    productos.value = respuesta.data
  } catch (error) {
    console.error("Error al cargar los productos:", error)
  }
}

const cerrarSesion = () => {
  localStorage.removeItem('sigfo_token')
  localStorage.removeItem('sigfo_becado')
  setAuthToken('')
  token.value = ''
  becadoActual.value = null
  isAuthenticated.value = false
  productos.value = []
  carrito.value = []
  tipoPago.value = 'efectivo'
  cuentaSeleccionada.value = ''
  montoEfectivo.value = ''
  montoTransferencia.value = ''
  errorPago.value = ''
  dniInput.value = ''
}

// agregar un producto al carrito
const agregarAlCarrito = (producto) => {
  // verificamos si ya esta
  const itemExiste = carrito.value.find(item => item.id === producto.id)
  const stockDisponible = producto.stock ?? producto.stock_maximo
  
  if (itemExiste) {
    // sumamos la cantidad teniendo en cuenta el stock
    if (producto.es_servicio || stockDisponible === null || itemExiste.cantidad < stockDisponible) {
      itemExiste.cantidad++
    }
  } else {
    carrito.value.push({
      id: producto.id,
      nombre: producto.nombre,
      precio: parseFloat(producto.precio),
      cantidad: 1,
      es_servicio: producto.es_servicio,
      stock_maximo: producto.stock
    })
  }
}

const restarCantidad = (item) => {
  if (item.cantidad > 1) {
    item.cantidad--
  } else {
    eliminarDelCarrito(item.id)
  }
}

const eliminarDelCarrito = (id) => {
  carrito.value = carrito.value.filter(item => item.id !== id)
}

// calculo del total de la venta
const totalVenta = computed(() => {
  return carrito.value.reduce((suma, item) => suma + (item.precio * item.cantidad), 0)
})

const esPagoCombinado = computed(() => tipoPago.value === 'combinado')
const esCuentaAbierta = computed(() => tipoPago.value === 'cuenta_abierta')

const totalCombinado = computed(() => {
  const efectivo = parseFloat(montoEfectivo.value || 0)
  const transferencia = parseFloat(montoTransferencia.value || 0)
  return efectivo + transferencia
})

const diferenciaCombinado = computed(() => {
  const diferencia = totalVenta.value - totalCombinado.value
  return Math.round(diferencia * 100) / 100
})

const pagoValido = computed(() => {
  if (carrito.value.length === 0) {
    return false
  }

  if (tipoPago.value === 'cuenta_abierta') {
    return Boolean(cuentaSeleccionada.value)
  }

  if (tipoPago.value === 'combinado') {
    return Math.abs(diferenciaCombinado.value) < 0.01
  }

  return true
})

watch(tipoPago, () => {
  errorPago.value = ''
  if (tipoPago.value !== 'combinado') {
    montoEfectivo.value = ''
    montoTransferencia.value = ''
  }
  if (tipoPago.value !== 'cuenta_abierta') {
    cuentaSeleccionada.value = ''
  }
})

const confirmarVenta = () => {
  errorPago.value = ''

  if (carrito.value.length === 0) {
    errorPago.value = 'No hay productos en el ticket.'
    return
  }

  if (tipoPago.value === 'cuenta_abierta' && !cuentaSeleccionada.value) {
    errorPago.value = 'Selecciona una cuenta abierta institucional para registrar la venta.'
    return
  }

  if (tipoPago.value === 'combinado' && !pagoValido.value) {
    errorPago.value = 'En pago combinado, la suma de efectivo y transferencia debe coincidir con el total.'
    return
  }

  const payloadVenta = {
    items: carrito.value.map(item => ({
      producto_id: item.id,
      cantidad: item.cantidad,
    })),
    tipo_pago: tipoPago.value,
    cuenta_abierta_id: esCuentaAbierta.value ? cuentaSeleccionada.value : null,
    monto_efectivo: tipoPago.value === 'combinado' ? Number(montoEfectivo.value || 0) : (tipoPago.value === 'efectivo' ? totalVenta.value : 0),
    monto_transferencia: tipoPago.value === 'combinado' ? Number(montoTransferencia.value || 0) : (tipoPago.value === 'transferencia' ? totalVenta.value : 0),
  }

  // TODO: conectar con endpoint real de ventas
  console.log('Venta lista para enviar:', payloadVenta)

  infoMensaje.value = 'Venta preparada correctamente. Falta conectar el endpoint para guardarla.'
  carrito.value = []
  tipoPago.value = 'efectivo'
}

onMounted(() => {
  const tokenGuardado = localStorage.getItem('sigfo_token')
  const becadoGuardado = localStorage.getItem('sigfo_becado')
  
  if (tokenGuardado && becadoGuardado) {
    token.value = tokenGuardado
    setAuthToken(token.value)
    becadoActual.value = JSON.parse(becadoGuardado)
    isAuthenticated.value = true
    obtenerProductos()
  }
})

</script>

<template>
  <div style="padding: 30px; font-family: sans-serif; max-width: 800px; margin: 0 auto;">
    
    <div v-if="!isAuthenticated" style="border: 1px solid #ccc; padding: 40px; border-radius: 8px; text-align: center; margin-top: 50px;">
      <h2>SiGFo - Acceso</h2>
      <p style="color: #666;">Ingresá tu DNI para fichar tu asistencia e iniciar sesión</p>
      
      <div style="margin: 20px 0;">
        <input 
          v-model="dniInput" 
          type="text" 
          placeholder="Ej: 12345678" 
          @keyup.enter="iniciarSesion"
          style="padding: 12px; width: 250px; font-size: 16px; text-align: center; border-radius: 4px; border: 1px solid #bbb;"
        />
      </div>
      
      <button @click="iniciarSesion" style="padding: 12px 24px; font-size: 16px; background-color: #28a745; color: white; border: none; border-radius: 4px; cursor: pointer;">
        Ingresar
      </button>

      <p v-if="errorMensaje" style="color: red; margin-top: 15px; font-weight: bold;">{{ errorMensaje }}</p>
    </div>

    <div v-else>
      <div style="display: flex; justify-content: space-between; align-items: center; background: #f4f4f4; padding: 10px 20px; border-radius: 4px;">
        <div>
          <span>Becado activo: <strong>{{ becadoActual.nombre }}</strong></span>
          <br>
          <small style="color: green;">{{ infoMensaje }}</small>
        </div>
        <button @click="cerrarSesion" style="padding: 6px 12px; background-color: #dc3545; color: white; border: none; border-radius: 4px; cursor: pointer;">
          Cerrar Sesión
        </button>
      </div>

      <h1 style="margin-top: 30px;">Panel de Ventas</h1>
      <hr>

      <div style="display: flex; gap: 30px; margin-top: 20px;">
        
        <div style="flex: 1; border: 1px solid #ddd; padding: 15px; border-radius: 6px;">
          <h3>Productos y Servicios</h3>
          <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
            <div 
              v-for="prod in productos" 
              :key="prod.id" 
              style="padding: 10px; border: 1px solid #eee; border-radius: 4px; display: flex; justify-content: space-between; align-items: center;"
            >
              <div>
                <strong>{{ prod.nombre }}</strong> <br>
                <span style="color: #28a745; font-weight: bold;">${{ prod.precio }}</span>
                <small style="color: #777; margin-left: 10px;">
                  ({{ prod.es_servicio ? 'Servicio' : 'Stock: ' + prod.stock }})
                </small>
              </div>
              <button 
                @click="agregarAlCarrito(prod)" 
                :disabled="!prod.es_servicio && prod.stock <= 0"
                style="padding: 6px 12px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;"
              >
                + Añadir
              </button>
            </div>
          </div>
        </div>

        <div style="flex: 1; border: 1px solid #ccc; padding: 15px; border-radius: 6px; background-color: #fafafa; display: flex; flex-direction: column; justify-content: space-between;">
          <div>
            <h3>Ticket Actual</h3>
            
            <p v-if="carrito.length === 0" style="color: #888; text-align: center; margin-top: 40px;">
              El carrito está vacío. Añadí productos de la lista.
            </p>
            
            <table v-else style="width: 100%; border-collapse: collapse;">
              <thead>
                <tr style="border-bottom: 2px solid #ddd; text-align: left;">
                  <th>Item</th>
                  <th style="text-align: center;">Cant.</th>
                  <th style="text-align: right;">Subtotal</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in carrito" :key="item.id" style="border-bottom: 1px solid #eee;">
                  <td style="padding: 10px 0;">{{ item.nombre }}</td>
                  <td style="text-align: center;">
                    <button @click="restarCantidad(item)" style="padding: 2px 6px;">-</button>
                    <span style="margin: 0 8px; font-weight: bold;">{{ item.cantidad }}</span>
                    <button @click="agregarAlCarrito(item)" style="padding: 2px 6px;">+</button>
                  </td>
                  <td style="text-align: right;">${{ (item.precio * item.cantidad).toFixed(2) }}</td>
                  <td style="text-align: right;">
                    <button @click="eliminarDelCarrito(item.id)" style="color: red; border: none; background: none; cursor: pointer;">❌</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="carrito.length > 0" style="margin-top: 30px; border-top: 2px dashed #bbb; padding-top: 15px;">
            <div style="display: flex; justify-content: space-between; font-size: 20px; font-weight: bold; margin-bottom: 15px;">
              <span>TOTAL:</span>
              <span style="color: #28a745;">${{ totalVenta.toFixed(2) }}</span>
            </div>

            <div style="margin-bottom: 15px; background: #eee; padding: 10px; border-radius: 4px;">
              <label style="margin-right: 15px;">
                <input type="radio" value="efectivo" v-model="tipoPago"> Efectivo
              </label>
              <label style="margin-right: 15px;">
                <input type="radio" value="transferencia" v-model="tipoPago"> Transferencia
              </label>
              <label style="margin-right: 15px;">
                <input type="radio" value="combinado" v-model="tipoPago"> Combinado
              </label>
              <label>
                <input type="radio" value="cuenta_abierta" v-model="tipoPago"> Cuenta Abierta
              </label>
            </div>

            <div v-if="esPagoCombinado" style="margin-bottom: 15px; background: #f5f5f5; padding: 10px; border-radius: 4px;">
              <h4 style="margin: 0 0 10px 0;">Detalle de pago combinado</h4>
              <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div>
                  <label style="display: block; margin-bottom: 6px;">Efectivo</label>
                  <input v-model="montoEfectivo" type="number" min="0" step="0.01" placeholder="0.00" style="width: 100%; padding: 8px;" />
                </div>
                <div>
                  <label style="display: block; margin-bottom: 6px;">Transferencia</label>
                  <input v-model="montoTransferencia" type="number" min="0" step="0.01" placeholder="0.00" style="width: 100%; padding: 8px;" />
                </div>
              </div>
              <small :style="{ color: pagoValido ? '#2e7d32' : '#c62828' }">
                Diferencia pendiente: ${{ diferenciaCombinado.toFixed(2) }}
              </small>
            </div>

            <div v-if="esCuentaAbierta" style="margin-bottom: 15px; background: #f5f5f5; padding: 10px; border-radius: 4px;">
              <label style="display: block; margin-bottom: 6px;">Cuenta abierta institucional</label>
              <select v-model="cuentaSeleccionada" style="width: 100%; padding: 8px;">
                <option value="">Seleccionar cuenta...</option>
                <option v-for="cuenta in cuentasAbiertas" :key="cuenta.id" :value="cuenta.id">
                  {{ cuenta.nombre }}
                </option>
              </select>
            </div>

            <p v-if="errorPago" style="color: #c62828; margin: 0 0 12px 0; font-weight: bold;">{{ errorPago }}</p>

            <button @click="confirmarVenta" :disabled="!pagoValido" :style="{ width: '100%', padding: '12px', fontSize: '18px', backgroundColor: pagoValido ? '#28a745' : '#9e9e9e', color: 'white', border: 'none', borderRadius: '4px', fontWeight: 'bold', cursor: pagoValido ? 'pointer' : 'not-allowed' }">
              Confirmar Venta
            </button>
          </div>

        </div>

      </div>
    </div>

  </div>
</template>

<style scoped>
</style>
