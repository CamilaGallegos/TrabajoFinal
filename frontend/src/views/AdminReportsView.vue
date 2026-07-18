<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const cargando = ref(false)
const error = ref('')
const incluirFinde = ref(false)
const semanaSeleccionada = ref('')
const movimientoDiaSemana = ref([])

const formatearFechaIso = (fecha) => {
  const year = fecha.getUTCFullYear()
  const month = String(fecha.getUTCMonth() + 1).padStart(2, '0')
  const day = String(fecha.getUTCDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const semanaActualIso = () => {
  const hoy = new Date()
  const fechaUtc = new Date(Date.UTC(hoy.getFullYear(), hoy.getMonth(), hoy.getDate()))
  const diaSemana = (fechaUtc.getUTCDay() + 6) % 7
  fechaUtc.setUTCDate(fechaUtc.getUTCDate() + 3 - diaSemana)

  const year = fechaUtc.getUTCFullYear()
  const primerJueves = new Date(Date.UTC(year, 0, 4))
  const primerDiaSemana = (primerJueves.getUTCDay() + 6) % 7
  primerJueves.setUTCDate(primerJueves.getUTCDate() + 3 - primerDiaSemana)

  const week = 1 + Math.round((fechaUtc - primerJueves) / (7 * 24 * 60 * 60 * 1000))
  return `${year}-W${String(week).padStart(2, '0')}`
}

const rangoSemana = computed(() => {
  const valor = semanaSeleccionada.value
  if (!valor || !valor.includes('-W')) {
    return { desde: '', hasta: '' }
  }

  const [yearPart, weekPart] = valor.split('-W')
  const year = Number(yearPart)
  const week = Number(weekPart)

  if (!year || !week) {
    return { desde: '', hasta: '' }
  }

  const fechaBase = new Date(Date.UTC(year, 0, 1 + (week - 1) * 7))
  const diaBase = fechaBase.getUTCDay() || 7
  if (diaBase <= 4) {
    fechaBase.setUTCDate(fechaBase.getUTCDate() - diaBase + 1)
  } else {
    fechaBase.setUTCDate(fechaBase.getUTCDate() + 8 - diaBase)
  }

  const inicio = new Date(fechaBase)
  const fin = new Date(fechaBase)
  fin.setUTCDate(inicio.getUTCDate() + 6)

  return {
    desde: formatearFechaIso(inicio),
    hasta: formatearFechaIso(fin),
  }
})

const rangoSemanaTexto = computed(() => {
  if (!rangoSemana.value.desde || !rangoSemana.value.hasta) {
    return ''
  }
  return `${rangoSemana.value.desde} al ${rangoSemana.value.hasta}`
})

const cargarMovimientoSemana = async () => {
  if (!rangoSemana.value.desde || !rangoSemana.value.hasta) {
    error.value = 'Selecciona una semana valida'
    return
  }

  cargando.value = true
  error.value = ''

  try {
    const respuesta = await axios.get('http://localhost:8000/api/reportes/dashboard-resumen/', {
      params: {
        fecha_desde: rangoSemana.value.desde,
        fecha_hasta: rangoSemana.value.hasta,
        incluir_finde: incluirFinde.value,
        _: Date.now(),
      },
    })

    movimientoDiaSemana.value = respuesta.data?.movimiento_dia_semana || []
  } catch (err) {
    movimientoDiaSemana.value = []
    error.value = 'No se pudieron cargar los reportes'
  } finally {
    cargando.value = false
  }
}

const movimientoSeries = computed(() => ([
  {
    name: 'Ventas',
    data: movimientoDiaSemana.value.map((item) => item.ventas || 0),
  },
]))

const movimientoOptions = computed(() => ({
  chart: {
    id: 'movimiento-dia-semana',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  colors: ['#0077B6'],
  plotOptions: {
    bar: {
      borderRadius: 8,
      columnWidth: '52%',
    },
  },
  dataLabels: {
    enabled: false,
  },
  xaxis: {
    categories: movimientoDiaSemana.value.map((item) => item.dia),
    labels: {
      style: {
        colors: '#334155',
        fontSize: '12px',
      },
    },
  },
  yaxis: {
    min: 0,
    title: {
      text: 'Cantidad de ventas',
      style: {
        color: '#475569',
      },
    },
    labels: {
      style: {
        colors: '#334155',
      },
    },
  },
  grid: {
    strokeDashArray: 4,
    borderColor: '#e2e8f0',
  },
  tooltip: {
    theme: 'light',
    y: {
      formatter: (valor) => `${valor} ventas`,
    },
  },
}))

onMounted(() => {
  semanaSeleccionada.value = semanaActualIso()
  cargarMovimientoSemana()
})
</script>

<template>
  <div class="reports-container">
    <header class="reports-header">
      <div>
        <h2>Reportes</h2>
      </div>

    </header>

    <div v-if="cargando" class="estado-msg">Cargando reportes...</div>
    <div v-else-if="error" class="estado-msg error">{{ error }}</div>

    <section v-else class="chart-grid">
      <article class="chart-card">
        <header class="chart-title">
          <h3>Movimientos por dia por semana</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Semana
            <input v-model="semanaSeleccionada" type="week" />
          </label>

          <label class="check-control">
            <input v-model="incluirFinde" type="checkbox" />
            Incluir finde
          </label>

          <button type="button" class="btn-refresh" @click="cargarMovimientoSemana">
            Actualizar
          </button>

          <small v-if="rangoSemanaTexto" class="week-range">Rango: {{ rangoSemanaTexto }}</small>
        </div>

        <div v-if="movimientoDiaSemana.length === 0" class="estado-msg">
          No hay datos para la semana seleccionada.
        </div>

        <apexchart
          v-else
          type="bar"
          height="320"
          :options="movimientoOptions"
          :series="movimientoSeries"
        />
      </article>
    </section>
  </div>
</template>

<style scoped>
.reports-container {
  width: 100%;
  display: grid;
  gap: 18px;
}

.reports-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 20px;
  border: 1px solid #d8dde6;
  border-radius: 16px;
  background: linear-gradient(135deg, #ffffff 0%, #f3f9fc 100%);
}

.reports-header h2 {
  margin: 0 0 6px;
  color: #08324a;
}

.reports-header p {
  margin: 0;
  color: #5b6b79;
  max-width: 560px;
}

.reports-actions {
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 10px;
}

.reports-actions label {
  display: grid;
  gap: 4px;
  font-size: 12px;
  color: #475569;
  font-weight: 600;
}

.reports-actions input[type='date'],
.reports-actions input[type='week'] {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 8px 10px;
  color: #0f172a;
}

.chart-actions {
  margin-bottom: 12px;
}

.week-range {
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
  padding-bottom: 8px;
}

.check-control {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 6px 8px;
}

.btn-refresh {
  border: 0;
  border-radius: 10px;
  padding: 9px 14px;
  background: #0077b6;
  color: #ffffff;
  font-weight: 700;
  cursor: pointer;
}

.btn-refresh:hover {
  background: #04689f;
}

.estado-msg {
  color: #5b6b79;
  font-size: 14px;
}

.estado-msg.error {
  color: #b91c1c;
}

.chart-grid {
  display: grid;
  gap: 14px;
}

.chart-card {
  border: 1px solid #d8dde6;
  border-radius: 16px;
  padding: 18px;
  background: #ffffff;
}

.chart-title h3 {
  margin: 0 0 6px;
  color: #0f172a;
}

.chart-title p {
  margin: 0 0 12px;
  color: #64748b;
  font-size: 14px;
}

@media (max-width: 900px) {
  .reports-header {
    flex-direction: column;
  }
}
</style>
