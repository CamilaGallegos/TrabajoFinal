import { computed, ref } from 'vue'
import axios from 'axios'

export function useCatalogo() {
  const productos = ref([])
  const cuentasAbiertas = ref([])
  const busquedaLibreria = ref('')
  const cargandoProductos = ref(false)

  const bloquesServicios = [
    {
      titulo: 'BLANCO Y NEGRO',
      destacado: false,
      items: [
        { base: 'Blanco y Negro', variante: 'Simple', etiqueta: 'simple faz' },
        { base: 'Blanco y Negro', variante: 'Doble', etiqueta: 'doble faz' },
      ],
    },
    {
      titulo: 'COLOR',
      destacado: true,
      items: [
        { base: 'Color', variante: 'Simple', etiqueta: 'simple faz' },
        { base: 'Color', variante: 'Doble', etiqueta: 'doble faz' },
      ],
    },
    {
      titulo: 'ESCANEO',
      destacado: false,
      items: [
        { base: 'Escaneo', variante: '', etiqueta: 'unidades' },
      ],
    },
    {
      titulo: 'DNI',
      destacado: true,
      items: [
        { base: 'DNI', variante: 'Simple', etiqueta: 'simple faz' },
        { base: 'DNI', variante: 'Doble', etiqueta: 'doble faz' },
      ],
    },
    {
      titulo: 'ANILLADO',
      destacado: false,
      items: [
        { base: 'Anillado', variante: '', etiqueta: 'copias a anillar' },
      ],
    },
  ]

  const libreriaFiltrada = computed(() => {
    if (!busquedaLibreria.value) return []
    return productos.value.filter((p) =>
      !p.es_servicio && p.nombre.toLowerCase().includes(busquedaLibreria.value.toLowerCase())
    )
  })

  const obtenerProductos = async () => {
    cargandoProductos.value = true
    try {
      const respuesta = await axios.get('http://localhost:8000/api/productos/')
      productos.value = respuesta.data
      return productos.value
    } catch (error) {
      console.error('Error al cargar los productos:', error)
      return []
    } finally {
      cargandoProductos.value = false
    }
  }

  const obtenerCuentasAbiertas = async () => {
    try {
      const respuesta = await axios.get('http://localhost:8000/api/cuentas-abiertas/')
      cuentasAbiertas.value = respuesta.data.map((cuenta) => ({
        id: cuenta.id,
        nombre: cuenta.nombre_departamento,
      }))
    } catch (error) {
      console.error('Error al cargar cuentas abiertas:', error)
      cuentasAbiertas.value = []
    }
  }

  const resetCatalogo = () => {
    productos.value = []
    cuentasAbiertas.value = []
    busquedaLibreria.value = ''
  }

  return {
    productos,
    cuentasAbiertas,
    busquedaLibreria,
    cargandoProductos,
    bloquesServicios,
    libreriaFiltrada,
    obtenerProductos,
    obtenerCuentasAbiertas,
    resetCatalogo,
  }
}
