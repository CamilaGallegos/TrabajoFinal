<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const resumen = ref({ actual: null, anterior: null, seleccionado: null })
const mesSeleccionado = ref('')
const cargando = ref(false)
const error = ref('')
const usuariosExpandido = ref({})
const modalUsuarioAbierto = ref(false)
const creandoUsuario = ref(false)
const errorUsuario = ref('')

const usuarioForm = ref({
  nombre: '',
  apellido: '',
  dni: '',
  legajo: '',
})

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
    usuariosExpandido.value = {}
  } catch (err) {
    resumen.value = { actual: null, anterior: null, seleccionado: null }
    usuariosExpandido.value = {}
    const status = err?.response?.status
    if (status === 401 || status === 403) {
      error.value = 'No autorizado. Es posible que tu sesión haya expirado o tu usuario esté inhabilitado.'
    } else {
      const detalle = err?.response?.data?.detail || err?.response?.data?.error || err?.message
      error.value = detalle ? `Error al cargar las asistencias: ${detalle}` : 'Error al cargar las asistencias'
    }
  } finally {
    cargando.value = false
  }
}

const abrirModalUsuario = () => {
  errorUsuario.value = ''
  usuarioForm.value = {
    nombre: '',
    apellido: '',
    dni: '',
    legajo: '',
  }
  modalUsuarioAbierto.value = true
}

const cerrarModalUsuario = () => {
  modalUsuarioAbierto.value = false
  errorUsuario.value = ''
}

const crearUsuario = async () => {
  if (!String(usuarioForm.value.nombre || '').trim() || !String(usuarioForm.value.dni || '').trim()) {
    errorUsuario.value = 'Nombre y DNI son obligatorios.'
    return
  }

  creandoUsuario.value = true
  errorUsuario.value = ''

  try {
    const payload = {
      nombre: String(usuarioForm.value.nombre || '').trim(),
      apellido: String(usuarioForm.value.apellido || '').trim(),
      dni: String(usuarioForm.value.dni || '').trim(),
      legajo: String(usuarioForm.value.legajo || '').trim(),
    }

    await axios.post('http://localhost:8000/api/becados-admin/', payload)
    await cargarResumen()
    cerrarModalUsuario()
  } catch (err) {
    const apiError = err?.response?.data
    if (typeof apiError === 'string') {
      errorUsuario.value = apiError
    } else if (apiError?.dni?.[0]) {
      errorUsuario.value = apiError.dni[0]
    } else if (apiError?.detail) {
      errorUsuario.value = apiError.detail
    } else {
      errorUsuario.value = 'No se pudo crear el usuario.'
    }
  } finally {
    creandoUsuario.value = false
  }
}

const cambiarEstadoUsuario = async (usuario, activo) => {
  if (!usuario?.becado_id) {
    return
  }

  const accion = activo ? 'habilitar' : 'inhabilitar'
  const confirmar = window.confirm(`¿Querés ${accion} a ${usuario.nombre_usuario}?`)
  if (!confirmar) {
    return
  }

  try {
    await axios.patch(`http://localhost:8000/api/becados-admin/${usuario.becado_id}/`, { activo })
    await cargarResumen()
  } catch (err) {
    error.value = 'No se pudo actualizar el estado del usuario.'
  }
}

const resumenMes = (clave) => resumen.value?.[clave] || { usuarios: [], cantidad_asistencias: 0, total_horas: 0, label: '' }

const mesActualSeleccionado = computed(() => {
  const seleccionado = mesSeleccionado.value || mesActualValor()
  return seleccionado === mesActualValor()
})

const panelTitulo = computed(() => (mesActualSeleccionado.value ? 'Mes actual' : 'Mes elegido'))
const panelDescripcion = computed(() => (
  mesActualSeleccionado.value
    ? 'Todas las asistencias de este mes'
    : 'Asistencias del mes seleccionado'
))

const resumenVisible = computed(() => resumenMes('seleccionado'))

const totalHorasTexto = (valor) => {
  const horasDecimal = Number(valor || 0)
  const minutosTotales = Math.max(0, Math.round(horasDecimal * 60))
  const horas = Math.floor(minutosTotales / 60)
  const minutos = minutosTotales % 60
  return `${horas} h ${String(minutos).padStart(2, '0')} min`
}

const textoSalida = (asistencia) => {
  if (asistencia.salida) {
    const textoBase = formatearFecha(asistencia.salida)
    if (asistencia.salida_motivo === 'expirada') {
      return `${textoBase} (expirada)`
    }
    if (asistencia.salida_motivo === 'sin_cierre') {
      return `${textoBase} (cierre automático)`
    }
    return textoBase
  }

  const entrada = new Date(asistencia.entrada)
  const ahora = new Date()
  const mismoMes = entrada.getFullYear() === ahora.getFullYear() && entrada.getMonth() === ahora.getMonth()
  return mismoMes ? 'Activo ahora' : 'Sin cierre'
}

const claveUsuario = (seccionKey, becadoId) => `${seccionKey}-${becadoId}`

const usuarioEstaExpandido = (seccionKey, becadoId) => Boolean(usuariosExpandido.value[claveUsuario(seccionKey, becadoId)])

const alternarUsuarioExpandido = (seccionKey, becadoId) => {
  const clave = claveUsuario(seccionKey, becadoId)
  usuariosExpandido.value[clave] = !usuariosExpandido.value[clave]
}

const asistenciasOrdenadas = (usuario) => {
  const asistencias = Array.isArray(usuario.asistencias) ? [...usuario.asistencias] : []
  return asistencias.sort((a, b) => new Date(b.entrada).getTime() - new Date(a.entrada).getTime())
}

const asistenciasVisibles = (seccionKey, usuario) => {
  const asistencias = asistenciasOrdenadas(usuario)
  if (usuarioEstaExpandido(seccionKey, usuario.becado_id)) {
    return asistencias
  }
  return asistencias.slice(0, 5)
}

const puedeExpandirUsuario = (usuario) => (usuario.asistencias?.length || 0) > 5

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
        <button type="button" class="btn-secondary" @click="abrirModalUsuario">Crear usuario</button>
        <input v-model="mesSeleccionado" type="month" class="month-input" />
        <button type="button" class="btn-refresh" @click="cargarResumen">Actualizar</button>
      </div>
    </header>

    <div v-if="cargando" class="estado-msg">Cargando asistencias...</div>
    <div v-else-if="error" class="estado-msg error">{{ error }}</div>

    <section v-else class="attendance-grid">
      <article class="attendance-panel">
        <header class="panel-header">
          <div>
            <h3>{{ panelTitulo }}</h3>
            <p>{{ panelDescripcion }}</p>
          </div>
          <div class="panel-meta">
            <span v-if="resumenVisible.label">{{ resumenVisible.label }}</span>
            <strong>{{ totalHorasTexto(resumenVisible.total_horas) }}</strong>
            <small>{{ resumenVisible.cantidad_asistencias }} asistencias</small>
          </div>
        </header>

        <div v-if="resumenVisible.usuarios.length === 0" class="estado-msg">
          No hay asistencias para este período
        </div>

        <div v-else class="usuarios-lista">
          <article v-for="usuario in resumenVisible.usuarios" :key="usuario.becado_id" class="usuario-card">
            <header class="usuario-header">
              <div>
                <h4>{{ usuario.nombre_usuario }}</h4>
                <p>Total del mes: {{ totalHorasTexto(usuario.total_horas) }}</p>
              </div>
              <div class="usuario-actions">
                <span v-if="usuario.activo === false" class="estado-chip">Inhabilitado</span>
                <button
                  type="button"
                  class="btn-secondary"
                  @click="cambiarEstadoUsuario(usuario, usuario.activo === false)"
                >
                  {{ usuario.activo === false ? 'Habilitar' : 'Inhabilitar' }}
                </button>
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
                <tr v-for="asistencia in asistenciasVisibles('seleccionado', usuario)" :key="asistencia.id">
                  <td>{{ formatearFecha(asistencia.entrada) }}</td>
                  <td>{{ textoSalida(asistencia) }}</td>
                  <td class="right">{{ totalHorasTexto(asistencia.horas) }}</td>
                </tr>
              </tbody>
            </table>

            <div v-if="puedeExpandirUsuario(usuario)" class="usuario-footer">
              <button
                type="button"
                class="btn-link"
                @click="alternarUsuarioExpandido('seleccionado', usuario.becado_id)"
              >
                {{ usuarioEstaExpandido('seleccionado', usuario.becado_id) ? 'Ver menos' : 'Ver más' }}
              </button>
            </div>
          </article>
        </div>
      </article>
    </section>

    <div v-if="modalUsuarioAbierto" class="modal-overlay" @click.self="cerrarModalUsuario">
      <section class="modal-card">
        <header>
          <h3>Crear usuario</h3>
          <p>Alta de nuevo becado para fichaje</p>
        </header>

        <div class="form-grid">
          <label>
            Nombre
            <input v-model="usuarioForm.nombre" type="text" maxlength="150" />
          </label>

          <label>
            Apellido
            <input v-model="usuarioForm.apellido" type="text" maxlength="150" />
          </label>

          <label>
            DNI
            <input v-model="usuarioForm.dni" type="text" maxlength="15" />
          </label>

          <label>
            Legajo
            <input v-model="usuarioForm.legajo" type="text" maxlength="20" />
          </label>
        </div>

        <p v-if="errorUsuario" class="estado-msg error">{{ errorUsuario }}</p>

        <footer class="modal-actions">
          <button type="button" class="btn-secondary" @click="cerrarModalUsuario">Cancelar</button>
          <button type="button" class="btn-refresh" :disabled="creandoUsuario" @click="crearUsuario">
            {{ creandoUsuario ? 'Creando...' : 'Crear usuario' }}
          </button>
        </footer>
      </section>
    </div>
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

.btn-secondary {
  border: 0;
  border-radius: 10px;
  padding: 8px 12px;
  background: #e2e8f0;
  color: #0f172a;
  font-weight: 600;
  cursor: pointer;
}

.btn-secondary:hover {
  background: #cbd5e1;
}

.btn-secondary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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

.usuario-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.estado-chip {
  border-radius: 999px;
  padding: 4px 8px;
  font-size: 11px;
  font-weight: 700;
  background: #fee2e2;
  color: #991b1b;
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

.usuario-footer {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.btn-link {
  border: 0;
  background: transparent;
  color: #0578af;
  font-weight: 600;
  font-size: 13px;
  cursor: pointer;
  padding: 4px 0;
}

.btn-link:hover {
  color: #046892;
  text-decoration: underline;
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

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: grid;
  place-items: center;
  padding: 16px;
  z-index: 20;
}

.modal-card {
  width: min(640px, 100%);
  background: #ffffff;
  border-radius: 16px;
  border: 1px solid #d8dde6;
  padding: 16px;
  display: grid;
  gap: 12px;
}

.modal-card h3 {
  margin: 0;
  color: #0f172a;
}

.modal-card p {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 13px;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}

.form-grid label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.form-grid input {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 10px;
  color: #0f172a;
  font: inherit;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
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

  .usuario-header {
    flex-direction: column;
  }

  .form-grid {
    grid-template-columns: 1fr;
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