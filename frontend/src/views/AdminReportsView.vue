<script setup>
import { computed, onMounted, ref } from 'vue'
import axios from 'axios'

const semanaMovimiento = ref('')
const incluirFindeMovimiento = ref(false)
const movimientoDiaSemana = ref([])
const cargandoMovimiento = ref(false)
const errorMovimiento = ref('')

const semanaHoras = ref('')
const incluirFindeHoras = ref(false)
const flujoDiaHora = ref([])
const cargandoHoras = ref(false)
const errorHoras = ref('')

const mesMetodo = ref('')
const preferenciaMetodo = ref([])
const cargandoMetodo = ref(false)
const errorMetodo = ref('')

const mesTotal = ref('')
const totalesEfectivoTransferencia = ref([])
const cargandoTotal = ref(false)
const errorTotal = ref('')

const mesTop = ref('')
const topProductos = ref([])
const cargandoTop = ref(false)
const errorTop = ref('')

const mesSaldos = ref('')
const saldosCuentas = ref([])
const cargandoSaldos = ref(false)
const errorSaldos = ref('')

const mesEvolucionDesde = ref('')
const mesEvolucionHasta = ref('')
const evolucionMensual = ref([])
const cargandoEvolucion = ref(false)
const errorEvolucion = ref('')

const obtenerMesActual = () => {
  const hoy = new Date()
  const year = hoy.getFullYear()
  const month = String(hoy.getMonth() + 1).padStart(2, '0')
  return `${year}-${month}`
}

const obtenerRangoMes = (valor) => {
  if (!valor || !valor.includes('-')) {
    return { desde: '', hasta: '' }
  }

  const [yearPart, monthPart] = valor.split('-')
  const year = Number(yearPart)
  const month = Number(monthPart)

  if (!year || !month || month < 1 || month > 12) {
    return { desde: '', hasta: '' }
  }

  const primerDia = new Date(Date.UTC(year, month - 1, 1))
  const ultimoDia = new Date(Date.UTC(year, month, 0))

  return {
    desde: formatearFechaIso(primerDia),
    hasta: formatearFechaIso(ultimoDia),
  }
}

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

const obtenerRangoSemana = (valor) => {
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
}

const rangoMovimiento = computed(() => obtenerRangoSemana(semanaMovimiento.value))
const rangoHoras = computed(() => obtenerRangoSemana(semanaHoras.value))
const rangoMetodo = computed(() => obtenerRangoMes(mesMetodo.value))
const rangoTotal = computed(() => obtenerRangoMes(mesTotal.value))
const rangoTop = computed(() => obtenerRangoMes(mesTop.value))
const rangoSaldos = computed(() => obtenerRangoMes(mesSaldos.value))
const rangoEvolucionDesde = computed(() => obtenerRangoMes(mesEvolucionDesde.value))
const rangoEvolucionHasta = computed(() => obtenerRangoMes(mesEvolucionHasta.value))

const rangoTexto = (rango) => {
  if (!rango.desde || !rango.hasta) {
    return ''
  }
  return `${rango.desde} al ${rango.hasta}`
}

const rangoMovimientoTexto = computed(() => rangoTexto(rangoMovimiento.value))
const rangoHorasTexto = computed(() => rangoTexto(rangoHoras.value))
const rangoMetodoTexto = computed(() => rangoTexto(rangoMetodo.value))
const rangoTotalTexto = computed(() => rangoTexto(rangoTotal.value))
const rangoTopTexto = computed(() => rangoTexto(rangoTop.value))
const rangoSaldosTexto = computed(() => rangoTexto(rangoSaldos.value))

const rangoEvolucionTexto = computed(() => {
  const desde = mesEvolucionDesde.value || ''
  const hasta = mesEvolucionHasta.value || ''
  if (!desde || !hasta) {
    return ''
  }
  return `${desde} a ${hasta}`
})

const consultarResumen = async ({ fechaDesde, fechaHasta, incluirFinde = false }) => {
  const respuesta = await axios.get('http://localhost:8000/api/reportes/dashboard-resumen/', {
    params: {
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      incluir_finde: incluirFinde,
      _: Date.now(),
    },
  })

  return respuesta.data || {}
}

const consultarCuentasAbiertas = async ({ fechaDesde, fechaHasta }) => {
  const respuesta = await axios.get('http://localhost:8000/api/cuentas-abiertas-resumen/', {
    params: {
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      _: Date.now(),
    },
  })

  return respuesta.data || {}
}

const consultarEvolucionCuentasAbiertas = async ({ fechaDesde, fechaHasta }) => {
  const respuesta = await axios.get('http://localhost:8000/api/reportes/cuentas-abiertas-evolucion/', {
    params: {
      fecha_desde: fechaDesde,
      fecha_hasta: fechaHasta,
      _: Date.now(),
    },
  })

  return respuesta.data || {}
}

const cargarMovimientoSemana = async () => {
  if (!rangoMovimiento.value.desde || !rangoMovimiento.value.hasta) {
    errorMovimiento.value = 'Selecciona una semana valida'
    return
  }

  cargandoMovimiento.value = true
  errorMovimiento.value = ''

  try {
    const data = await consultarResumen({
      fechaDesde: rangoMovimiento.value.desde,
      fechaHasta: rangoMovimiento.value.hasta,
      incluirFinde: incluirFindeMovimiento.value,
    })
    movimientoDiaSemana.value = data.movimiento_dia_semana || []
  } catch (err) {
    movimientoDiaSemana.value = []
    errorMovimiento.value = 'No se pudo cargar el movimiento semanal'
  } finally {
    cargandoMovimiento.value = false
  }
}

const cargarHorasSemana = async () => {
  if (!rangoHoras.value.desde || !rangoHoras.value.hasta) {
    errorHoras.value = 'Selecciona una semana valida'
    return
  }

  cargandoHoras.value = true
  errorHoras.value = ''

  try {
    const data = await consultarResumen({
      fechaDesde: rangoHoras.value.desde,
      fechaHasta: rangoHoras.value.hasta,
      incluirFinde: incluirFindeHoras.value,
    })
    flujoDiaHora.value = data.flujo_dia_hora || []
  } catch (err) {
    flujoDiaHora.value = []
    errorHoras.value = 'No se pudo cargar el flujo por dia y hora'
  } finally {
    cargandoHoras.value = false
  }
}

const cargarMetodosPago = async () => {
  if (!rangoMetodo.value.desde || !rangoMetodo.value.hasta) {
    errorMetodo.value = 'Selecciona un mes valido'
    return
  }

  cargandoMetodo.value = true
  errorMetodo.value = ''

  try {
    const data = await consultarResumen({
      fechaDesde: rangoMetodo.value.desde,
      fechaHasta: rangoMetodo.value.hasta,
    })
    preferenciaMetodo.value = data.preferencia_pago || []
  } catch (err) {
    preferenciaMetodo.value = []
    errorMetodo.value = 'No se pudo cargar la preferencia de pago'
  } finally {
    cargandoMetodo.value = false
  }
}

const cargarTotalesEfectivoTransferencia = async () => {
  if (!rangoTotal.value.desde || !rangoTotal.value.hasta) {
    errorTotal.value = 'Selecciona un mes valido'
    return
  }

  cargandoTotal.value = true
  errorTotal.value = ''

  try {
    const data = await consultarResumen({
      fechaDesde: rangoTotal.value.desde,
      fechaHasta: rangoTotal.value.hasta,
    })
    totalesEfectivoTransferencia.value = data.totales_efectivo_transferencia || []
  } catch (err) {
    totalesEfectivoTransferencia.value = []
    errorTotal.value = 'No se pudo cargar los totales'
  } finally {
    cargandoTotal.value = false
  }
}

const cargarTopProductos = async () => {
  if (!rangoTop.value.desde || !rangoTop.value.hasta) {
    errorTop.value = 'Selecciona un mes valido'
    return
  }

  cargandoTop.value = true
  errorTop.value = ''

  try {
    const data = await consultarResumen({
      fechaDesde: rangoTop.value.desde,
      fechaHasta: rangoTop.value.hasta,
    })
    topProductos.value = data.top_productos || []
  } catch (err) {
    topProductos.value = []
    errorTop.value = 'No se pudo cargar el top de productos'
  } finally {
    cargandoTop.value = false
  }
}

const cargarSaldosCuentasAbiertas = async () => {
  if (!rangoSaldos.value.desde || !rangoSaldos.value.hasta) {
    errorSaldos.value = 'Selecciona un mes valido'
    return
  }

  cargandoSaldos.value = true
  errorSaldos.value = ''

  try {
    const data = await consultarCuentasAbiertas({
      fechaDesde: rangoSaldos.value.desde,
      fechaHasta: rangoSaldos.value.hasta,
    })
    saldosCuentas.value = (data.cuentas || []).map((cuenta) => ({
      cuenta: cuenta.nombre_departamento,
      saldo: Number(cuenta.total_pendiente || 0),
    }))
  } catch (err) {
    saldosCuentas.value = []
    errorSaldos.value = 'No se pudo cargar el saldo de cuentas abiertas'
  } finally {
    cargandoSaldos.value = false
  }
}

const cargarEvolucionMensualCuentasAbiertas = async () => {
  const desde = rangoEvolucionDesde.value.desde
  const hasta = rangoEvolucionHasta.value.hasta

  if (!desde || !hasta) {
    errorEvolucion.value = 'Selecciona un rango mensual valido'
    return
  }

  if (mesEvolucionDesde.value > mesEvolucionHasta.value) {
    errorEvolucion.value = 'El mes desde no puede ser mayor al mes hasta'
    evolucionMensual.value = []
    return
  }

  cargandoEvolucion.value = true
  errorEvolucion.value = ''

  try {
    const data = await consultarEvolucionCuentasAbiertas({
      fechaDesde: desde,
      fechaHasta: hasta,
    })
    evolucionMensual.value = data.evolucion || []
  } catch (err) {
    evolucionMensual.value = []
    errorEvolucion.value = 'No se pudo cargar la evolución mensual'
  } finally {
    cargandoEvolucion.value = false
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

const diasHeatmap = computed(() => (
  incluirFindeHoras.value
    ? ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    : ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes']
))

const horasHeatmap = computed(() => {
  const horas = []
  for (let hora = 9; hora <= 20; hora += 1) {
    horas.push(`${String(hora).padStart(2, '0')}:00`)
  }
  return horas
})

const horasSeries = computed(() => {
  const lookup = new Map(
    flujoDiaHora.value.map((item) => [`${item.dia}|${item.hora}`, Number(item.ventas || 0)])
  )

  return diasHeatmap.value.map((dia) => ({
    name: dia,
    data: horasHeatmap.value.map((hora) => ({
      x: hora,
      y: lookup.get(`${dia}|${hora}`) ?? 0,
    })),
  }))
})

const horasOptions = computed(() => ({
  chart: {
    id: 'flujo-dia-hora-semana',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  plotOptions: {
    heatmap: {
      radius: 6,
      shadeIntensity: 0.6,
      colorScale: {
        ranges: [
          { from: 0, to: 0, color: '#e2e8f0', name: 'Sin ventas' },
          { from: 1, to: 4, color: '#c7f9cc', name: 'Bajo' },
          { from: 5, to: 9, color: '#80ed99', name: 'Medio' },
          { from: 10, to: 9999, color: '#06d6a0', name: 'Alto' },
        ],
      },
    },
  },
  dataLabels: {
    enabled: false,
  },
  grid: {
    strokeDashArray: 4,
    borderColor: '#e2e8f0',
  },
  xaxis: {
    labels: {
      style: {
        colors: '#334155',
        fontSize: '12px',
      },
    },
    title: {
      text: 'Hora del dia',
      style: {
        color: '#475569',
      },
    },
  },
  yaxis: {
    labels: {
      style: {
        colors: '#334155',
      },
    },
    title: {
      text: 'Dia de la semana',
      style: {
        color: '#475569',
      },
    },
  },
  tooltip: {
    theme: 'light',
    custom: ({ series, seriesIndex, dataPointIndex, w }) => {
      const dia = w.config.series[seriesIndex].name
      const hora = w.config.series[seriesIndex].data[dataPointIndex].x
      const valor = series[seriesIndex][dataPointIndex]
      return `<div style="padding:8px 10px;"><strong>${dia}</strong><br/>${hora}: ${valor} ventas</div>`
    },
  },
}))

const metodosSeries = computed(() => preferenciaMetodo.value.map((item) => item.transacciones))

const metodosOptions = computed(() => ({
  chart: {
    id: 'preferencia-pago-semana',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  colors: ['#06D6A0', '#0077B6', '#F59E0B', '#DC2626'],
  labels: preferenciaMetodo.value.map((item) => item.label),
  plotOptions: {
    pie: {
      donut: {
        size: '75%',
        labels: {
          show: true,
          name: {
            show: false,
          },
          value: {
            show: true,
            fontSize: '13px',
            color: '#475569',
            formatter: (valor) => `${valor}`,
          },
          total: {
            show: true,
            label: 'Total',
            color: '#0f172a',
            formatter: () => `${preferenciaMetodo.value.reduce((acc, item) => acc + item.transacciones, 0)} transacciones`,
          },
        },
      },
    },
  },
  dataLabels: {
    enabled: true,
    formatter: (valor, { series, seriesIndex }) => {
      const item = preferenciaMetodo.value[seriesIndex]
      return item ? `${item.porcentaje.toFixed(1)}%` : '0%'
    },
    style: {
      fontSize: '12px',
      colors: ['#ffffff'],
    },
  },
  legend: {
    position: 'bottom',
    labels: {
      colors: '#334155',
    },
  },
  tooltip: {
    theme: 'light',
    y: {
      formatter: (valor) => `${valor} transacciones`,
    },
  },
}))

const totalSeries = computed(() => ([
  {
    name: 'Monto recaudado',
    data: totalesEfectivoTransferencia.value.map((item) => item.monto || 0),
  },
]))

const totalOptions = computed(() => ({
  chart: {
    id: 'total-efectivo-transferencia',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  colors: ['#06D6A0'],
  plotOptions: {
    bar: {
      borderRadius: 8,
      columnWidth: '55%',
      dataLabels: {
        position: 'top',
      },
    },
  },
  dataLabels: {
    enabled: true,
    offsetY: -20,
    style: {
      colors: ['#0f172a'],
      fontSize: '12px',
      fontWeight: '600',
    },
    formatter: (valor) => `$${valor.toFixed(2)}`,
  },
  xaxis: {
    categories: totalesEfectivoTransferencia.value.map((item) => item.label),
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
      text: 'Monto ($)',
      style: {
        color: '#475569',
      },
    },
    labels: {
      style: {
        colors: '#334155',
      },
      formatter: (valor) => `$${valor.toFixed(0)}`,
    },
  },
  grid: {
    strokeDashArray: 4,
    borderColor: '#e2e8f0',
  },
  tooltip: {
    theme: 'light',
    y: {
      formatter: (valor) => `$${valor.toFixed(2)}`,
    },
  },
}))

const topSeries = computed(() => ([
  {
    name: 'Unidades vendidas',
    data: topProductos.value.map((item) => ({
      x: item.producto,
      y: item.unidades || 0,
    })),
  },
]))

const topOptions = computed(() => ({
  chart: {
    id: 'top-10-productos',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  colors: ['#3B82F6'],
  plotOptions: {
    bar: {
      horizontal: true,
      borderRadius: 6,
      barHeight: '70%',
      dataLabels: {
        position: 'right',
      },
    },
  },
  dataLabels: {
    enabled: true,
    style: {
      colors: ['#0f172a'],
      fontSize: '11px',
      fontWeight: '600',
    },
  },
  xaxis: {
    min: 0,
    title: {
      text: 'Unidades vendidas',
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
  yaxis: {
    labels: {
      style: {
        colors: '#334155',
        fontSize: '12px',
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
      formatter: (valor) => `${valor} unidades`,
    },
  },
}))

const saldosSeries = computed(() => ([
  {
    name: 'Saldo pendiente',
    data: saldosCuentas.value.map((item) => item.saldo || 0),
  },
]))

const saldosOptions = computed(() => ({
  chart: {
    id: 'saldo-cuentas-abiertas',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  colors: ['#FACC15'],
  plotOptions: {
    bar: {
      horizontal: true,
      borderRadius: 8,
      barHeight: '65%',
    },
  },
  dataLabels: {
    enabled: true,
    formatter: (valor) => `$${valor.toFixed(2)}`,
    style: {
      colors: ['#713f12'],
      fontSize: '11px',
      fontWeight: '600',
    },
  },
  xaxis: {
    categories: saldosCuentas.value.map((item) => item.cuenta),
    labels: {
      style: {
        colors: '#334155',
        fontSize: '12px',
      },
    },
    title: {
      text: 'Saldo pendiente ($)',
      style: {
        color: '#475569',
      },
    },
  },
  yaxis: {
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
      formatter: (valor) => `$${valor.toFixed(2)}`,
    },
  },
}))

const evolucionSeries = computed(() => ([
  {
    name: 'Saldos pendientes',
    data: evolucionMensual.value.map((item) => Number(item.deuda_generada || 0)),
  },
  {
    name: 'Pagos cobrados',
    data: evolucionMensual.value.map((item) => Number(item.pagos_cobrados || 0)),
  },
]))

const evolucionOptions = computed(() => ({
  chart: {
    id: 'evolucion-deuda-pagos',
    type: 'area',
    toolbar: { show: false },
    fontFamily: 'Poppins, sans-serif',
  },
  colors: ['#f59e0b', '#0ea5e9'],
  stroke: {
    curve: 'smooth',
    width: 3,
  },
  fill: {
    type: 'gradient',
    gradient: {
      shadeIntensity: 1,
      opacityFrom: 0.22,
      opacityTo: 0.04,
      stops: [0, 90, 100],
    },
  },
  markers: {
    size: 4,
    strokeWidth: 0,
  },
  dataLabels: {
    enabled: false,
  },
  xaxis: {
    categories: evolucionMensual.value.map((item) => item.periodo),
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
      text: 'Monto ($)',
      style: {
        color: '#475569',
      },
    },
    labels: {
      style: {
        colors: '#334155',
      },
      formatter: (valor) => `$${valor.toFixed(0)}`,
    },
  },
  grid: {
    strokeDashArray: 4,
    borderColor: '#e2e8f0',
  },
  legend: {
    position: 'top',
    horizontalAlign: 'left',
    labels: {
      colors: '#334155',
    },
  },
  tooltip: {
    theme: 'light',
    y: {
      formatter: (valor) => `$${valor.toFixed(2)}`,
    },
  },
}))

onMounted(() => {
  const semanaActual = semanaActualIso()
  const mesActual = obtenerMesActual()
  const fechaActual = new Date(`${mesActual}-01T00:00:00`)
  const fechaDesdeEvolucion = new Date(fechaActual)
  fechaDesdeEvolucion.setMonth(fechaActual.getMonth() - 5)

  const yearDesde = fechaDesdeEvolucion.getFullYear()
  const monthDesde = String(fechaDesdeEvolucion.getMonth() + 1).padStart(2, '0')
  const mesDesdePorDefecto = `${yearDesde}-${monthDesde}`

  semanaMovimiento.value = semanaActual
  semanaHoras.value = semanaActual
  mesMetodo.value = mesActual
  mesTotal.value = mesActual
  mesTop.value = mesActual
  mesSaldos.value = mesActual
  mesEvolucionDesde.value = mesDesdePorDefecto
  mesEvolucionHasta.value = mesActual
  cargarMovimientoSemana()
  cargarHorasSemana()
  cargarMetodosPago()
  cargarTotalesEfectivoTransferencia()
  cargarTopProductos()
  cargarSaldosCuentasAbiertas()
  cargarEvolucionMensualCuentasAbiertas()
})
</script>

<template>
  <div class="reports-container">
    <header class="reports-header">
      <div>
        <h2>Reportes</h2>
        <p>Acá podes ver diferentes reportes y estadísticas</p>
      </div>

    </header>

    <section class="chart-grid">
      <article class="chart-card">
        <header class="chart-title">
          <h3>Movimientos por dia por semana</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Semana
            <input v-model="semanaMovimiento" type="week" />
          </label>

          <label class="check-control">
            <input v-model="incluirFindeMovimiento" type="checkbox" />
            Incluir finde
          </label>

          <button type="button" class="btn-refresh" @click="cargarMovimientoSemana">
            Actualizar
          </button>

          <small v-if="rangoMovimientoTexto" class="week-range">Rango: {{ rangoMovimientoTexto }}</small>
        </div>

        <div v-if="cargandoMovimiento" class="estado-msg">Cargando movimiento semanal...</div>
        <div v-else-if="errorMovimiento" class="estado-msg error">{{ errorMovimiento }}</div>
        <div v-else-if="movimientoDiaSemana.length === 0" class="estado-msg">
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

      <article class="chart-card">
        <header class="chart-title">
          <h3>Flujo por dia y hora</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Semana
            <input v-model="semanaHoras" type="week" />
          </label>

          <label class="check-control">
            <input v-model="incluirFindeHoras" type="checkbox" />
            Incluir finde
          </label>

          <button type="button" class="btn-refresh" @click="cargarHorasSemana">
            Actualizar
          </button>

          <small v-if="rangoHorasTexto" class="week-range">Rango: {{ rangoHorasTexto }}</small>
        </div>

        <div v-if="cargandoHoras" class="estado-msg">Cargando horas pico...</div>
        <div v-else-if="errorHoras" class="estado-msg error">{{ errorHoras }}</div>
        <div v-else-if="flujoDiaHora.length === 0" class="estado-msg">
          No hay datos de flujo para la semana seleccionada.
        </div>

        <apexchart
          v-else
          type="heatmap"
          height="320"
          :options="horasOptions"
          :series="horasSeries"
        />
      </article>

      <article class="chart-card">
        <header class="chart-title">
          <h3>Preferencia de metodos de pago</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Mes
            <input v-model="mesMetodo" type="month" />
          </label>

          <button type="button" class="btn-refresh" @click="cargarMetodosPago">
            Actualizar
          </button>

          <small v-if="rangoMetodoTexto" class="week-range">Rango: {{ rangoMetodoTexto }}</small>
        </div>

        <div v-if="cargandoMetodo" class="estado-msg">Cargando metodos de pago...</div>
        <div v-else-if="errorMetodo" class="estado-msg error">{{ errorMetodo }}</div>
        <div v-else-if="preferenciaMetodo.length === 0" class="estado-msg">
          No hay datos de metodos de pago para el mes seleccionado
        </div>

        <apexchart
          v-else
          type="donut"
          height="340"
          :options="metodosOptions"
          :series="metodosSeries"
        />
      </article>

      <article class="chart-card">
        <header class="chart-title">
          <h3>Total mensual en efectivo y transferencia</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Mes
            <input v-model="mesTotal" type="month" />
          </label>

          <button type="button" class="btn-refresh" @click="cargarTotalesEfectivoTransferencia">
            Actualizar
          </button>

          <small v-if="rangoTotalTexto" class="week-range">Rango: {{ rangoTotalTexto }}</small>
        </div>

        <div v-if="cargandoTotal" class="estado-msg">Cargando totales...</div>
        <div v-else-if="errorTotal" class="estado-msg error">{{ errorTotal }}</div>
        <div v-else-if="totalesEfectivoTransferencia.length === 0" class="estado-msg">
          No hay datos de recaudacion para el mes seleccionad
        </div>

        <apexchart
          v-else
          type="bar"
          height="320"
          :options="totalOptions"
          :series="totalSeries"
        />
      </article>

      <article class="chart-card chart-card-full">
        <header class="chart-title">
          <h3>Top 10 productos y servicios mas vendidos</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Mes
            <input v-model="mesTop" type="month" />
          </label>

          <button type="button" class="btn-refresh" @click="cargarTopProductos">
            Actualizar
          </button>

          <small v-if="rangoTopTexto" class="week-range">Rango: {{ rangoTopTexto }}</small>
        </div>

        <div v-if="cargandoTop" class="estado-msg">Cargando top 10...</div>
        <div v-else-if="errorTop" class="estado-msg error">{{ errorTop }}</div>
        <div v-else-if="topProductos.length === 0" class="estado-msg">
          No hay datos de ventas para el mes seleccionado
        </div>

        <apexchart
          v-else
          type="bar"
          height="500"
          :options="topOptions"
          :series="topSeries"
        />
      </article>

      <article class="chart-card chart-card-full">
        <header class="chart-title">
          <h3>Saldo pendiente total por cuenta abierta</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Mes
            <input v-model="mesSaldos" type="month" />
          </label>

          <button type="button" class="btn-refresh" @click="cargarSaldosCuentasAbiertas">
            Actualizar
          </button>

          <small v-if="rangoSaldosTexto" class="week-range">Rango: {{ rangoSaldosTexto }}</small>
        </div>

        <div v-if="cargandoSaldos" class="estado-msg">Cargando saldos pendientes...</div>
        <div v-else-if="errorSaldos" class="estado-msg error">{{ errorSaldos }}</div>
        <div v-else-if="saldosCuentas.length === 0" class="estado-msg">
          No hay cuentas abiertas con saldo para el mes seleccionado
        </div>

        <apexchart
          v-else
          type="bar"
          height="360"
          :options="saldosOptions"
          :series="saldosSeries"
        />
      </article>

      <article class="chart-card chart-card-full">
        <header class="chart-title">
          <h3>Evolución mensual: saldos pendientes vs pagos cobrados</h3>
        </header>

        <div class="reports-actions chart-actions">
          <label>
            Desde
            <input v-model="mesEvolucionDesde" type="month" />
          </label>

          <label>
            Hasta
            <input v-model="mesEvolucionHasta" type="month" />
          </label>

          <button type="button" class="btn-refresh" @click="cargarEvolucionMensualCuentasAbiertas">
            Actualizar
          </button>

          <small v-if="rangoEvolucionTexto" class="week-range">Rango: {{ rangoEvolucionTexto }}</small>
        </div>

        <div v-if="cargandoEvolucion" class="estado-msg">Cargando evolución mensual...</div>
        <div v-else-if="errorEvolucion" class="estado-msg error">{{ errorEvolucion }}</div>
        <div v-else-if="evolucionMensual.length === 0" class="estado-msg">
          No hay datos de saldos pendientes/pagos para el rango seleccionado
        </div>

        <apexchart
          v-else
          type="area"
          height="360"
          :options="evolucionOptions"
          :series="evolucionSeries"
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
.reports-actions input[type='week'],
.reports-actions input[type='month'] {
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
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-auto-rows: max-content;
}

.chart-card {
  border: 1px solid #d8dde6;
  border-radius: 16px;
  padding: 18px;
  background: #ffffff;
}

.chart-card-full {
  grid-column: 1 / -1;
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

@media (max-width: 1200px) {
  .chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 900px) {
  .reports-header {
    flex-direction: column;
  }
}
</style>
