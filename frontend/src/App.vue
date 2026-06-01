<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

//variable para guardar los productos y fichaje
const dniInput = ref('')
const isAuthenticated = ref(false)
const token = ref('')
const becadoActual = ref(null)
const productos = ref([])
const errorMensaje = ref('')
const infoMensaje = ref('')

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
  dniInput.value = ''
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

      <div style="margin-top: 20px;">
        <h3>Productos Disponibles:</h3>
        <ul>
          <li v-for="prod in productos" :key="prod.id" style="margin-bottom: 8px;">
            <strong>{{ prod.nombre }}</strong> - ${{ prod.precio }}
            <span style="color: gray; font-size: 0.9em; margin-left: 10px;">[{{ prod.categoria_nombre }}]</span>
          </li>
        </ul>
      </div>
    </div>

  </div>
</template>

<style scoped>
</style>
