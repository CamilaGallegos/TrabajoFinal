import { computed, ref, watch } from 'vue'

export function usePago({ carrito, totalVenta, onCuentaAbiertaSeleccionada }) {
  const tipoPago = ref('efectivo')
  const cuentaSeleccionada = ref('')
  const montoEfectivo = ref('')
  const montoTransferencia = ref('')
  const errorPago = ref('')

  const esPagoCombinado = computed(() => tipoPago.value === 'combinado')
  const esCuentaAbierta = computed(() => tipoPago.value === 'cuenta_abierta')

  const totalCombinado = computed(() => {
    const efectivo = parseFloat(montoEfectivo.value || 0)
    const transferencia = parseFloat(montoTransferencia.value || 0)
    return efectivo + transferencia
  })

  const diferenciaCombinado = computed(() => {
    const diferencia = totalVenta.value - totalCombinado.value
    return Math.round(diferencia * 100) / 100
  })

  const pagoValido = computed(() => {
    if (carrito.value.length === 0) {
      return false
    }

    if (tipoPago.value === 'cuenta_abierta') {
      return Boolean(cuentaSeleccionada.value)
    }

    if (tipoPago.value === 'combinado') {
      return Math.abs(diferenciaCombinado.value) < 0.01
    }

    return true
  })

  watch(tipoPago, () => {
    errorPago.value = ''
    if (tipoPago.value !== 'combinado') {
      montoEfectivo.value = ''
      montoTransferencia.value = ''
    }
    if (tipoPago.value !== 'cuenta_abierta') {
      cuentaSeleccionada.value = ''
    } else if (onCuentaAbiertaSeleccionada) {
      onCuentaAbiertaSeleccionada()
    }
  })

  const resetPago = () => {
    tipoPago.value = 'efectivo'
    cuentaSeleccionada.value = ''
    montoEfectivo.value = ''
    montoTransferencia.value = ''
    errorPago.value = ''
  }

  const validarPrevioConfirmacion = () => {
    errorPago.value = ''

    if (carrito.value.length === 0) {
      errorPago.value = 'No hay productos seleccionados para pagar'
      return false
    }

    if (tipoPago.value === 'cuenta_abierta' && !cuentaSeleccionada.value) {
      errorPago.value = 'Selecciona una cuenta abierta para registrar la venta'
      return false
    }

    if (tipoPago.value === 'combinado' && !pagoValido.value) {
      errorPago.value = 'En pago combinado, la suma de efectivo y transferencia debe coincidir con el total de la venta'
      return false
    }

    return true
  }

  const construirPayloadVenta = () => {
    return {
      items: carrito.value.map((item) => ({
        producto_id: item.id,
        cantidad: item.cantidad,
      })),
      tipo_pago: tipoPago.value,
      cuenta_abierta_id: esCuentaAbierta.value ? cuentaSeleccionada.value : null,
      monto_efectivo: tipoPago.value === 'combinado'
        ? Number(montoEfectivo.value || 0)
        : (tipoPago.value === 'efectivo' ? totalVenta.value : 0),
      monto_transferencia: tipoPago.value === 'combinado'
        ? Number(montoTransferencia.value || 0)
        : (tipoPago.value === 'transferencia' ? totalVenta.value : 0),
    }
  }

  return {
    tipoPago,
    cuentaSeleccionada,
    montoEfectivo,
    montoTransferencia,
    errorPago,
    esPagoCombinado,
    esCuentaAbierta,
    diferenciaCombinado,
    pagoValido,
    resetPago,
    validarPrevioConfirmacion,
    construirPayloadVenta,
  }
}
