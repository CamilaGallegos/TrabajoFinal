<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

//variable para guardar los productos
const productos = ref([])

const obtenerProductos = async () => {
  try {
    const respuesta = await axios.get('http://localhost:8000/api/productos/')
    productos.value = respuesta.data
  } catch (error) {
    console.error("Error al conectar con la API de Django:", error)
  }
}

onMounted(() => {
  obtenerProductos()
})
</script>

<template>
  <div style="padding: 20px; font-family: sans-serif;">
    <h1>SiGFo CURZAS - Panel de Ventas</h1>
    <hr>
    
    <h2>Productos disponibles:</h2>
    
    <p v-if="productos.length === 0">Cargando productos...</p>
    
    <ul v-else>
      <li v-for="prod in productos" :key="prod.id">
        <strong>{{ prod.nombre }}</strong> - ${{ prod.precio }} 
        <span v-if="prod.stock !== null">(Stock: {{ prod.stock }})</span>
        <span v-else>(Servicio)</span>
        <small style="color: gray; margin-left: 10px;">[{{ prod.categoria_nombre }}]</small>
      </li>
    </ul>
  </div>
</template>

<style scoped>
</style>
