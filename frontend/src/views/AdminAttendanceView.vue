<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const resumen = ref({ actual: null, anterior: null, seleccionado: null })
const mesSeleccionado = ref('')
const cargando = ref(false)
const error = ref('')

const formatearFecha = (fechaIso) => {
  if (!fechaIso) return 'Sin horario'
  const fecha = new Date(fechaIso)
  return fecha.toLocaleString('es-AR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const mesActualValor = () => {
  const hoy = new Date()
  return `${hoy.getFullYear()}-${String(hoy.getMonth() + 1).padStart(2, '0')}`
}

const mesAnteriorValor = () => {
  const hoy = new Date()
  const anterior = new Date(hoy.getFullYear(), hoy.getMonth() - 1, 1)
  return `${anterior.getFullYear()}-${String(anterior.getMonth() + 1).padStart(2, '0')}`
}

const cargarResumen = async () => {
  cargando.value = true
  error.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/asistencias/resumen/', {
      params: {
        mes: mesSeleccionado.value || mesActualValor(),
        _: Date.now(),
      },
    })
    resumen.value = respuesta.data || { actual: null, anterior: null, seleccionado: null }
  } catch (err) {
    resumen.value = { actual: null, anterior: null, seleccionado: null }
    error.value = 'Error al cargar las asistencias'
  } finally {
    cargando.value = false
  }
}

const secciones = computed(() => ([
  { key: 'actual', titulo: 'Mes actual', descripcion: 'Todas las asistencias de este mes' },
  { key: 'anterior', titulo: 'Mes anterior', descripcion: 'Total de horas y asistencias del mes pasado' },
  { key: 'seleccionado', titulo: 'Mes elegido', descripcion: 'Asistencias del mes seleccionado' },
]))

const resumenMes = (clave) => resumen.value?.[clave] || { usuarios: [], cantidad_asistencias: 0, total_horas: 0, label: '' }

const totalHorasTexto = (valor) => {
  const horasDecimal = Number(valor || 0)
  const minutosTotales = Math.max(0, Math.round(horasDecimal * 60))
  const horas = Math.floor(minutosTotales / 60)
  const minutos = minutosTotales % 60
  return `${horas} h ${String(minutos).padStart(2, '0')} min`
}

const textoSalida = (asistencia) => {
  if (asistencia.salida) {
    return formatearFecha(asistencia.salida)
  }

  const entrada = new Date(asistencia.entrada)
  const ahora = new Date()
  const mismoMes = entrada.getFullYear() === ahora.getFullYear() && entrada.getMonth() === ahora.getMonth()
  return mismoMes ? 'Activo ahora' : 'Sin cierre'
}

onMounted(() => {
  mesSeleccionado.value = mesActualValor()
  cargarResumen()
})
</script>

<template>
  <div class="attendance-container">
    <header class="attendance-header">
      <div>
        <h2>Asistencia</h2>
      </div>

      <div class="attendance-actions">
        <input v-model="mesSeleccionado" type="month" class="month-input" />
        <button type="button" class="btn-refresh" @click="cargarResumen">Actualizar</button>
      </div>
    </header>

    <div v-if="cargando" class="estado-msg">Cargando asistencias...</div>
    <div v-else-if="error" class="estado-msg error">{{ error }}</div>

    <section v-else class="attendance-grid">
      <article v-for="seccion in secciones" :key="seccion.key" class="attendance-panel">
        <header class="panel-header">
          <div>
            <h3>{{ seccion.titulo }}</h3>
            <p>{{ seccion.descripcion }}</p>
          </div>
          <div class="panel-meta">
            <span v-if="resumenMes(seccion.key).label">{{ resumenMes(seccion.key).label }}</span>
            <strong>{{ totalHorasTexto(resumenMes(seccion.key).total_horas) }}</strong>
            <small>{{ resumenMes(seccion.key).cantidad_asistencias }} asistencias</small>
          </div>
        </header>

        <div v-if="resumenMes(seccion.key).usuarios.length === 0" class="estado-msg">
          No hay asistencias para este período
        </div>

        <div v-else class="usuarios-lista">
          <article v-for="usuario in resumenMes(seccion.key).usuarios" :key="usuario.becado_id" class="usuario-card">
            <header class="usuario-header">
              <div>
                <h4>{{ usuario.nombre_usuario }}</h4>
                <p>Total del mes: {{ totalHorasTexto(usuario.total_horas) }}</p>
              </div>
            </header>

            <table class="asistencias-table">
              <thead>
                <tr>
                  <th>Entrada</th>
                  <th>Salida</th>
                  <th class="right">Horas</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="asistencia in usuario.asistencias" :key="asistencia.id">
                  <td>{{ formatearFecha(asistencia.entrada) }}</td>
                  <td>{{ textoSalida(asistencia) }}</td>
                  <td class="right">{{ totalHorasTexto(asistencia.horas) }}</td>
                </tr>
              </tbody>
            </table>
          </article>
        </div>
      </article>
    </section>
  </div>
</template>

<style scoped>
.attendance-container {
  width: 100%;
  display: grid;
  gap: 20px;
}

.attendance-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #d8dde6;
}

.attendance-header h2 {
  margin: 0 0 8px;
  color: #08324a;
}

.attendance-header p {
  margin: 0;
  color: #5b6b79;
}

.attendance-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.month-input {
  padding: 8px 10px;
  border: 1px solid #d8dde6;
  border-radius: 10px;
  background: #ffffff;
}

.btn-refresh {
  border: 0;
  border-radius: 10px;
  padding: 8px 12px;
  background: #0578af;
  color: #ffffff;
  font-weight: 600;
  cursor: pointer;
}

.btn-refresh:hover {
  background: #046892;
}

.estado-msg {
  color: #5b6b79;
  font-size: 14px;
}

.estado-msg.error {
  color: #b91c1c;
}

.attendance-grid {
  display: grid;
  gap: 16px;
}

.attendance-panel {
  padding: 18px;
  border-radius: 16px;
  background: #ffffff;
  border: 1px solid #d8dde6;
  display: grid;
  gap: 16px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
}

.panel-header h3 {
  margin: 0 0 6px;
  color: #0f172a;
}

.panel-header p {
  margin: 0;
  color: #64748b;
  font-size: 14px;
}

.panel-meta {
  display: grid;
  gap: 4px;
  justify-items: end;
  text-align: right;
}

.panel-meta span {
  color: #475569;
  font-size: 12px;
  text-transform: uppercase;
  font-weight: 700;
}

.panel-meta strong {
  color: #0578af;
  font-size: 18px;
}

.panel-meta small {
  color: #64748b;
}

.usuarios-lista {
  display: grid;
  gap: 14px;
}

.usuario-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 14px;
  background: #f8fbfd;
}

.usuario-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.usuario-header h4 {
  margin: 0 0 4px;
  color: #0f172a;
}

.usuario-header p {
  margin: 0;
  color: #64748b;
  font-size: 13px;
}

.asistencias-table {
  width: 100%;
  border-collapse: collapse;
  background: #ffffff;
  border-radius: 10px;
  overflow: hidden;
}

.asistencias-table th,
.asistencias-table td {
  padding: 10px 12px;
  border-bottom: 1px solid #eef2f7;
  font-size: 13px;
  color: #334155;
  text-align: left;
}

.asistencias-table th {
  background: #eef7fb;
  color: #0f172a;
  font-size: 12px;
  text-transform: uppercase;
}

.asistencias-table .right {
  text-align: right;
}

@media (max-width: 760px) {
  .attendance-header,
  .panel-header {
    flex-direction: column;
  }

  .attendance-actions {
    width: 100%;
    flex-wrap: wrap;
  }

  .panel-meta {
    justify-items: start;
    text-align: left;
  }

  .asistencias-table {
    display: block;
    overflow-x: auto;
  }
}
</style>