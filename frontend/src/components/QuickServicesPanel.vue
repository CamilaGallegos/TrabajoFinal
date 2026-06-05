<script setup>
const props = defineProps({
  bloquesServicios: {
    type: Array,
    required: true,
  },
  obtenerCantidadNumerica: {
    type: Function,
    required: true,
  },
  obtenerCantidadCarrito: {
    type: Function,
    required: true,
  },
  servicioActivo: {
    type: Function,
    required: true,
  },
  busquedaLibreria: {
    type: String,
    required: true,
  },
  libreriaFiltrada: {
    type: Array,
    required: true,
  },
})

const emit = defineEmits([
  'disminuir-servicio',
  'agregar-servicio',
  'actualizar-cantidad-servicio',
  'update:busquedaLibreria',
  'agregar-libreria',
])

const onBusquedaInput = (event) => {
  emit('update:busquedaLibreria', event.target.value)
}
</script>

<template>
  <div class="quick-panel">
    <div
      v-for="bloque in props.bloquesServicios"
      :key="bloque.titulo"
      :class="['servicio-bloque', { destacado: bloque.destacado }]"
    >
      <h3>{{ bloque.titulo }}</h3>
      <div class="servicio-rows">
        <div
          v-for="fila in bloque.items"
          :key="`${fila.base}-${fila.variante}`"
          class="servicio-row"
        >
          <span class="servicio-label">{{ fila.etiqueta }}</span>
          <div class="servicio-actions">
            <button
              class="qty-btn"
              :disabled="props.obtenerCantidadNumerica(fila.base, fila.variante) === 0"
              @click="emit('disminuir-servicio', fila.base, fila.variante)"
            >
              -
            </button>
            <input
              type="number"
              min="0"
              step="1"
              class="qty-input"
              :value="props.obtenerCantidadNumerica(fila.base, fila.variante)"
              @change="emit('actualizar-cantidad-servicio', fila.base, fila.variante, $event.target.value)"
            />
            <button class="qty-btn" @click="emit('agregar-servicio', fila.base, fila.variante)">+
            </button>
            <button
              :class="['switch-pill', { activo: props.servicioActivo(fila.base, fila.variante) }]"
              @click="emit('agregar-servicio', fila.base, fila.variante)"
            >
              {{ props.servicioActivo(fila.base, fila.variante) ? 'ON' : 'OFF' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="servicio-bloque libreria-bloque">
      <h3>LIBRERIA</h3>

      <div class="search-wrap">
        <input
          :value="props.busquedaLibreria"
          type="text"
          placeholder="Buscar articulo de libreria..."
          class="search-input"
          @input="onBusquedaInput"
        />
        <span class="search-icon">🔍</span>
      </div>

      <div v-if="props.busquedaLibreria" class="search-results">
        <button
          v-for="prod in props.libreriaFiltrada"
          :key="prod.id"
          class="search-item"
          @click="emit('agregar-libreria', prod)"
        >
          <span>{{ prod.nombre }}</span>
          <span class="price">${{ prod.precio }}</span>
        </button>
        <div v-if="props.libreriaFiltrada.length === 0" class="empty-search">
          No se encontraron articulos.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.quick-panel {
  border: 1px solid #d8dde6;
  border-radius: 14px;
  background: #fff;
  padding: 16px;
  max-height: 80vh;
  overflow: auto;
}

.servicio-bloque {
  background: #eef2f6;
  border-radius: 10px;
  padding: 12px;
  margin-bottom: 14px;
}

.servicio-bloque.destacado {
  background: #dce7f1;
}

.servicio-bloque h3 {
  margin: 0 0 8px;
  font-size: 34px;
  letter-spacing: 1px;
  font-weight: 300;
}

.servicio-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin: 8px 0;
}

.servicio-label {
  font-size: 30px;
  text-transform: lowercase;
}

.servicio-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.qty-btn {
  width: 30px;
  height: 30px;
  border: 1px solid #4b5563;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
  font-size: 18px;
}

.qty-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.qty-input {
  width: 76px;
  text-align: center;
  border: 1px solid #1f2937;
  border-radius: 8px;
  font-weight: 700;
  font-size: 18px;
  padding: 4px 6px;
  background: #fff;
}

.switch-pill {
  min-width: 58px;
  padding: 5px 8px;
  border: none;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: #d1d5db;
  color: #344054;
  cursor: pointer;
}

.switch-pill.activo {
  background: #00b488;
  color: #ffffff;
}

.libreria-bloque {
  background: #f6f8fb;
}

.search-wrap {
  position: relative;
  margin-bottom: 10px;
}

.search-input {
  width: 100%;
  padding: 12px 40px 12px 14px;
  border-radius: 14px;
  border: 2px solid #3a4453;
  font-size: 14px;
  box-sizing: border-box;
}

.search-icon {
  position: absolute;
  right: 12px;
  top: 10px;
}

.search-results {
  border: 1px solid #d9e0ea;
  border-radius: 8px;
  max-height: 180px;
  overflow-y: auto;
  background: #fff;
}

.search-item {
  width: 100%;
  border: none;
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #edf2f7;
  background: #fff;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.search-item:hover {
  background: #f8fbff;
}

.price {
  color: #1f7a3e;
  font-weight: 700;
}

.empty-search {
  color: #6b7280;
  text-align: center;
  padding: 10px;
}

@media (max-width: 1080px) {
  .servicio-bloque h3 {
    font-size: 24px;
  }

  .servicio-label {
    font-size: 22px;
  }
}

@media (max-width: 640px) {
  .servicio-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
