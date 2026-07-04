<script setup>
import { onMounted, ref, computed } from 'vue'
import axios from 'axios'
import { useCatalogo } from '../composables/useCatalogo'

const { productos, cargandoProductos, obtenerProductos } = useCatalogo()

const productosOrdenados = computed(() => {
  // ordenado por servicios primero
  return [...productos.value].sort((a, b) => {
    if ((a.es_servicio ? 1 : 0) === (b.es_servicio ? 1 : 0)) {
      return (a.nombre || '').localeCompare(b.nombre || '')
    }
    return a.es_servicio ? -1 : 1
  })
})

const modalOpen = ref(false)
const modalMode = ref(null)
const modalProducto = ref(null)

const formData = ref({
  nombre: '',
  precio: '',
  stock: '',
  es_servicio: false,
})

const feedback = ref({ show: false, message: '', type: 'success' })

const mostrarFeedback = (message, type = 'success') => {
  feedback.value = { show: true, message, type }
  window.clearTimeout(mostrarFeedback.timeout)
  mostrarFeedback.timeout = window.setTimeout(() => {
    feedback.value.show = false
  }, 2500)
}

const cargarProductos = async () => {
  await obtenerProductos()
}

const formatoStock = (producto) => {
  if (producto.es_servicio) {
    return 'Servicio'
  }
  return producto.stock === null || producto.stock === undefined ? 'N/A' : producto.stock
}

const abrirModalCrear = () => {
  modalMode.value = 'crear'
  modalProducto.value = null
  formData.value = { nombre: '', precio: '', stock: '', es_servicio: false }
  modalOpen.value = true
}

const abrirModalEditarPrecio = (producto) => {
  modalMode.value = 'precio'
  modalProducto.value = producto
  formData.value = { precio: String(producto.precio) }
  modalOpen.value = true
}

const abrirModalEditarNombre = (producto) => {
  modalMode.value = 'editar'
  modalProducto.value = producto
  formData.value = { nombre: producto.nombre }
  modalOpen.value = true
}

const abrirModalModificarStock = (producto) => {
  modalMode.value = 'stock'
  modalProducto.value = producto
  formData.value = { stock: String(producto.stock || 0) }
  modalOpen.value = true
}

// Se elimina el producto pero se conserva en la base de datos
const confirmDeleteOpen = ref(false)
const productoToDelete = ref(null)

const abrirConfirmDelete = (producto) => {
  productoToDelete.value = producto
  confirmDeleteOpen.value = true
}

const cancelarConfirmDelete = () => {
  productoToDelete.value = null
  confirmDeleteOpen.value = false
}

const confirmarEliminar = async () => {
  try {
    await axios.delete(`http://localhost:8000/api/productos/${productoToDelete.value.id}/`)
    mostrarFeedback('Producto eliminado correctamente')
    cancelarConfirmDelete()
    productos.value = []
    await obtenerProductos()
  } catch (error) {
    mostrarFeedback('No se pudo eliminar el producto', 'error')
  }
}

const cerrarModal = () => {
  modalOpen.value = false
  modalMode.value = null
  modalProducto.value = null
  formData.value = { nombre: '', precio: '', stock: '', es_servicio: false }
}

const guardarProducto = async () => {
  try {
    if (modalMode.value === 'crear') {
      const payload = {
        nombre: formData.value.nombre,
        precio: formData.value.precio,
        stock: formData.value.stock ? parseInt(formData.value.stock) : null,
        es_servicio: formData.value.es_servicio,
      }
      await axios.post('http://localhost:8000/api/productos/', payload)
      mostrarFeedback('Producto creado correctamente')
    } else if (modalMode.value === 'precio') {
      await axios.patch(`http://localhost:8000/api/productos/${modalProducto.value.id}/`, {
        precio: formData.value.precio,
      })
      mostrarFeedback('Precio actualizado correctamente')
    } else if (modalMode.value === 'editar') {
      await axios.patch(`http://localhost:8000/api/productos/${modalProducto.value.id}/`, {
        nombre: formData.value.nombre,
      })
      mostrarFeedback('Nombre actualizado correctamente')
    } else if (modalMode.value === 'stock') {
      await axios.patch(`http://localhost:8000/api/productos/${modalProducto.value.id}/`, {
        stock: formData.value.stock ? parseInt(formData.value.stock) : null,
      })
      mostrarFeedback('Stock actualizado correctamente')
    }
    cerrarModal()
    productos.value = []
    await obtenerProductos()
  } catch (error) {
    mostrarFeedback('No se pudo completar la acción', 'error')
  }
}

onMounted(cargarProductos)
</script>

<template>
  <div class="stock-container">
    <header class="stock-header">
      <div>
        <h1>Inventario</h1>
        <p>Gestiona productos, precios y stock disponible en el sistema</p>
      </div>
      <button type="button" class="btn-crear" @click="abrirModalCrear">+ Crear Producto</button>
    </header>

    <div v-if="feedback.show" class="feedback-banner" :class="feedback.type">
      {{ feedback.message }}
    </div>

    <section class="stock-table-card">
      <div v-if="cargandoProductos" class="stock-loading">Cargando productos...</div>
      <div v-else-if="productosOrdenados.length === 0" class="stock-empty">No hay productos disponibles.</div>
      <table v-else class="stock-table">
        <thead>
          <tr>
            <th>Producto</th>
            <th>Precio</th>
            <th>Stock</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="producto in productosOrdenados" :key="producto.id">
            <td>{{ producto.nombre }}</td>
            <td>${{ Number(producto.precio).toFixed(2) }}</td>
            <td>{{ formatoStock(producto) }}</td>
            <td class="col-acciones">
                <button type="button" class="btn-accion btn-editar" @click="abrirModalEditarNombre(producto)">
                  Editar nombre
                </button>
                <button type="button" class="btn-accion btn-precio" @click="abrirModalEditarPrecio(producto)">
                  Editar precio
                </button>
                <button v-if="!producto.es_servicio" type="button" class="btn-accion btn-stock" @click="abrirModalModificarStock(producto)">
                  Modificar stock
                </button>
                <button type="button" class="btn-accion btn-eliminar" @click="abrirConfirmDelete(producto)">
                  Eliminar
                </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>

    <div v-if="modalOpen" class="modal-overlay" @click.self="cerrarModal">
      <div class="modal">
        <div class="modal-header">
          <h2 v-if="modalMode === 'crear'">Crear Producto</h2>
          <h2 v-else-if="modalMode === 'precio'">Editar Precio</h2>
          <h2 v-else-if="modalMode === 'stock'">Modificar Stock</h2>
          <button type="button" class="modal-close" @click="cerrarModal">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="modalMode === 'crear'" class="form-group">
            <label>Nombre del producto</label>
            <input v-model="formData.nombre" type="text" placeholder="Ej: Papel A4" />

            <label>Precio</label>
            <input v-model="formData.precio" type="number" step="0.01" placeholder="0.00" />

            <label>Stock</label>
            <input v-model="formData.stock" type="number" placeholder="0" />

            <label class="checkbox-label">
              <input v-model="formData.es_servicio" type="checkbox" />
              Es un servicio
            </label>
          </div>

          <div v-else-if="modalMode === 'precio'" class="form-group">
            <label>Nuevo precio para: <strong>{{ modalProducto?.nombre }}</strong></label>
            <input v-model="formData.precio" type="number" step="0.01" placeholder="0.00" />
          </div>

          <div v-else-if="modalMode === 'editar'" class="form-group">
            <label>Editar nombre para: <strong>{{ modalProducto?.nombre }}</strong></label>
            <input v-model="formData.nombre" type="text" placeholder="Nombre del producto" />
          </div>

          <div v-else-if="modalMode === 'stock'" class="form-group">
            <label>Nuevo stock para: <strong>{{ modalProducto?.nombre }}</strong></label>
            <input v-model="formData.stock" type="number" placeholder="0" />
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn-cancel" @click="cerrarModal">Cancelar</button>
          <button type="button" class="btn-save" @click="guardarProducto">Guardar</button>
        </div>
      </div>
    </div>
    
    <div v-if="confirmDeleteOpen" class="modal-overlay" @click.self="cancelarConfirmDelete">
      <div class="modal">
        <div class="modal-header">
          <h2>Confirmar eliminación</h2>
          <button type="button" class="modal-close" @click="cancelarConfirmDelete">✕</button>
        </div>
        <div class="modal-body">
          <p>¿Estas seguro/a de eliminar el producto <strong>{{ productoToDelete?.nombre }}</strong>?</p>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn-cancel" @click="cancelarConfirmDelete">Cancelar</button>
          <button type="button" class="btn-save" @click="confirmarEliminar">Confirmar eliminación</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.stock-container {
  width: 100%;
  display: grid;
  gap: 20px;
}

.stock-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #d8dde6;
}

.stock-header h1 {
  margin: 0 0 8px;
  color: #08324a;
  font-size: clamp(1.5rem, 2vw, 2rem);
}

.stock-header p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
  max-width: 640px;
}

.btn-crear {
  border: none;
  border-radius: 10px;
  padding: 10px 16px;
  font-weight: 700;
  background: #0578af;
  color: #fff;
  cursor: pointer;
  white-space: nowrap;
}

.btn-crear:hover {
  background: #045b84;
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

.stock-table-card {
  width: 100%;
  background: #ffffff;
  border: 1px solid #d8dee7;
  border-radius: 16px;
  overflow: hidden;
}

.stock-loading,
.stock-empty {
  padding: 28px;
  color: #475569;
  text-align: center;
}

.stock-table {
  width: 100%;
  border-collapse: collapse;
}

.stock-table th,
.stock-table td {
  padding: 14px 16px;
  text-align: left;
}

.stock-table thead {
  background: #f1f8ff;
}

.stock-table th {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
  border-bottom: 1px solid #e2e8f0;
}

.stock-table td {
  border-bottom: 1px solid #eef2f7;
  color: #475569;
  font-size: 14px;
}

.stock-table tr:last-child td {
  border-bottom: none;
}

.col-acciones {
  display: flex;
  gap: 8px;
}

.btn-accion {
  border: 1px solid #0578af;
  background: transparent;
  color: #0578af;
  padding: 6px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}

.btn-accion:hover {
  background: #e8f3fb;
}

.btn-eliminar {
  border-color: #ef4444;
  color: #ef4444;
}

.btn-eliminar:hover {
  background: #fff1f2;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: grid;
  place-items: center;
  z-index: 50;
}

.modal {
  background: #ffffff;
  border-radius: 18px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.3);
  width: min(500px, 90vw);
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  color: #08324a;
}

.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  cursor: pointer;
  color: #64748b;
}

.modal-body {
  padding: 24px;
}

.form-group {
  display: grid;
  gap: 12px;
}

.form-group label {
  font-weight: 600;
  color: #0f172a;
  font-size: 14px;
}

.form-group input {
  padding: 10px 12px;
  border: 1px solid #d8dee7;
  border-radius: 8px;
  font-size: 14px;
}

.form-group input:focus {
  outline: none;
  border-color: #0578af;
  box-shadow: 0 0 0 3px rgba(5, 120, 175, 0.1);
}

.checkbox-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: normal;
  cursor: pointer;
}

.modal-footer {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 20px 24px;
  border-top: 1px solid #e2e8f0;
}

.btn-cancel {
  border: 1px solid #d8dee7;
  background: #ffffff;
  color: #475569;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel:hover {
  background: #f8fafc;
}

.btn-save {
  border: none;
  background: #0578af;
  color: #ffffff;
  padding: 10px 18px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.btn-save:hover {
  background: #045b84;
}

@media (max-width: 760px) {
  .stock-table th,
  .stock-table td {
    padding: 10px 8px;
  }

  .col-acciones {
    flex-direction: column;
  }

  .btn-accion {
    width: 100%;
  }
}
</style>
