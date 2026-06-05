import { computed, ref } from 'vue'

export function useCarrito({ productos, cargandoProductos, obtenerProductos }) {
  const carrito = ref([])

  const agregarAlCarrito = (producto) => {
    const itemExiste = carrito.value.find((item) => item.id === producto.id)
    const stockDisponible = producto.stock ?? producto.stock_maximo

    if (itemExiste) {
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
        stock_maximo: producto.stock,
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
    carrito.value = carrito.value.filter((item) => item.id !== id)
  }

  const normalizarNombre = (texto = '') => {
    return String(texto)
      .toLowerCase()
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^a-z0-9]+/g, ' ')
      .trim()
  }

  const nombreEsperadoServicio = (nombreBase, variante = '') => {
    if (!variante) {
      return normalizarNombre(nombreBase)
    }
    return normalizarNombre(`${nombreBase} ${variante} Faz`)
  }

  const coincidePorPalabras = (nombreProducto, esperado) => {
    const productoNormalizado = normalizarNombre(nombreProducto)
    const palabras = esperado.split(' ').filter(Boolean)
    return palabras.every((palabra) => productoNormalizado.includes(palabra))
  }

  const buscarProductoServicio = (nombreBase, variante = '') => {
    const esperado = nombreEsperadoServicio(nombreBase, variante)
    return productos.value.find((p) => coincidePorPalabras(p.nombre, esperado))
  }

  const buscarItemServicioEnCarrito = (nombreBase, variante = '') => {
    const esperado = nombreEsperadoServicio(nombreBase, variante)
    return carrito.value.find((i) => coincidePorPalabras(i.nombre, esperado))
  }

  const disminuirServicioRapido = (nombreBase, variante = '') => {
    const itemCarrito = buscarItemServicioEnCarrito(nombreBase, variante)
    if (itemCarrito) {
      restarCantidad(itemCarrito)
    }
  }

  const agregarServicioRapido = async (nombreBase, variante = '') => {
    if (productos.value.length === 0 && !cargandoProductos.value) {
      await obtenerProductos()
    }

    const esperado = nombreEsperadoServicio(nombreBase, variante)
    const productoMatch = buscarProductoServicio(nombreBase, variante)

    if (productoMatch) {
      agregarAlCarrito(productoMatch)
    } else {
      if (productos.value.length === 0) {
        alert('todavia no hay productos cargados')
        return
      }
      alert(`Alerta: No se encontro un producto que contenga "${esperado}", volve a intentarlo`)
    }
  }

  const actualizarCantidadServicio = async (nombreBase, variante = '', valorIngresado = 0) => {
    if (productos.value.length === 0 && !cargandoProductos.value) {
      await obtenerProductos()
    }

    const cantidadObjetivo = Math.max(0, parseInt(valorIngresado, 10) || 0)
    const itemCarrito = buscarItemServicioEnCarrito(nombreBase, variante)

    if (cantidadObjetivo === 0) {
      if (itemCarrito) {
        eliminarDelCarrito(itemCarrito.id)
      }
      return
    }

    if (!itemCarrito) {
      const productoMatch = buscarProductoServicio(nombreBase, variante)
      if (!productoMatch) {
        const esperado = nombreEsperadoServicio(nombreBase, variante)
        alert(`Alerta: No se encontro un producto que contenga "${esperado}", volve a intentarlo`)
        return
      }

      carrito.value.push({
        id: productoMatch.id,
        nombre: productoMatch.nombre,
        precio: parseFloat(productoMatch.precio),
        cantidad: cantidadObjetivo,
        es_servicio: productoMatch.es_servicio,
        stock_maximo: productoMatch.stock,
      })
      return
    }

    itemCarrito.cantidad = cantidadObjetivo
  }

  const obtenerCantidadCarrito = (nombreBase, variante = '') => {
    const item = buscarItemServicioEnCarrito(nombreBase, variante)
    return item ? item.cantidad : ''
  }

  const obtenerCantidadNumerica = (nombreBase, variante = '') => {
    const cantidad = obtenerCantidadCarrito(nombreBase, variante)
    return Number(cantidad || 0)
  }

  const servicioActivo = (nombreBase, variante = '') => {
    return obtenerCantidadNumerica(nombreBase, variante) > 0
  }

  const totalVenta = computed(() => {
    return carrito.value.reduce((suma, item) => suma + (item.precio * item.cantidad), 0)
  })

  const resetCarrito = () => {
    carrito.value = []
  }

  return {
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
  }
}
