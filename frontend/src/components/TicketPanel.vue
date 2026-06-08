<script setup>
import { computed } from 'vue'

const props = defineProps({
  carrito: {
    type: Array,
    required: true,
  },
  totalVenta: {
    type: Number,
    required: true,
  },
  tipoPago: {
    type: String,
    required: true,
  },
  esPagoCombinado: {
    type: Boolean,
    required: true,
  },
  esCuentaAbierta: {
    type: Boolean,
    required: true,
  },
  montoEfectivo: {
    type: [String, Number],
    required: true,
  },
  montoTransferencia: {
    type: [String, Number],
    required: true,
  },
  pagoValido: {
    type: Boolean,
    required: true,
  },
  diferenciaCombinado: {
    type: Number,
    required: true,
  },
  cuentasAbiertas: {
    type: Array,
    required: true,
  },
  cuentaSeleccionada: {
    type: [String, Number],
    required: true,
  },
  errorPago: {
    type: String,
    default: '',
  },
})

const emit = defineEmits([
  'restar-cantidad',
  'agregar-al-carrito',
  'eliminar-del-carrito',
  'update:tipoPago',
  'update:montoEfectivo',
  'update:montoTransferencia',
  'update:cuentaSeleccionada',
  'confirmar-venta',
])

const tipoPagoModel = computed({
  get: () => props.tipoPago,
  set: (value) => emit('update:tipoPago', value),
})

const montoEfectivoModel = computed({
  get: () => props.montoEfectivo,
  set: (value) => emit('update:montoEfectivo', value),
})

const montoTransferenciaModel = computed({
  get: () => props.montoTransferencia,
  set: (value) => emit('update:montoTransferencia', value),
})

const cuentaSeleccionadaModel = computed({
  get: () => props.cuentaSeleccionada,
  set: (value) => emit('update:cuentaSeleccionada', value),
})
</script>

<template>
  <div class="ticket-panel">
    <h3>Ticket</h3>

    <p v-if="props.carrito.length === 0" class="empty-ticket">
      El carrito esta vacio, agrega productos
    </p>

    <table v-else class="ticket-table">
      <thead>
        <tr>
          <th>Item</th>
          <th class="center">Cant.</th>
          <th class="right">Subtotal</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in props.carrito" :key="item.id">
          <td>{{ item.nombre }}</td>
          <td class="center qty-inline">
            <button class="qty-btn" @click="emit('restar-cantidad', item)">-</button>
            <span class="qty-current">{{ item.cantidad }}</span>
            <button class="qty-btn" @click="emit('agregar-al-carrito', item)">+</button>
          </td>
          <td class="right">${{ (item.precio * item.cantidad).toFixed(2) }}</td>
          <td class="right">
            <button class="delete-btn" @click="emit('eliminar-del-carrito', item.id)">X</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="props.carrito.length > 0" class="checkout-box">
      <div class="total-line">
        <span>TOTAL:</span>
        <span class="price-total">${{ props.totalVenta.toFixed(2) }}</span>
      </div>

      <div class="payment-types">
        <label><input v-model="tipoPagoModel" type="radio" value="efectivo" /> Efectivo</label>
        <label><input v-model="tipoPagoModel" type="radio" value="transferencia" /> Transferencia</label>
        <label><input v-model="tipoPagoModel" type="radio" value="combinado" /> Combinado</label>
        <label><input v-model="tipoPagoModel" type="radio" value="cuenta_abierta" /> Cuenta Abierta</label>
      </div>

      <div v-if="props.esPagoCombinado" class="pay-grid">
        <div>
          <label>Efectivo</label>
          <input v-model="montoEfectivoModel" type="number" min="0" step="0.01" placeholder="0.00" />
        </div>
        <div>
          <label>Transferencia</label>
          <input v-model="montoTransferenciaModel" type="number" min="0" step="0.01" placeholder="0.00" />
        </div>
        <small :class="['diff-text', { ok: props.pagoValido }]">
          Diferencia pendiente: ${{ props.diferenciaCombinado.toFixed(2) }}
        </small>
      </div>

      <div v-if="props.esCuentaAbierta" class="cuenta-wrap">
        <label>Cuenta abierta institucional</label>
        <select v-model="cuentaSeleccionadaModel">
          <option value="">Seleccionar cuenta...</option>
          <option v-for="cuenta in props.cuentasAbiertas" :key="cuenta.id" :value="cuenta.id">
            {{ cuenta.nombre }}
          </option>
        </select>
      </div>

      <p v-if="props.errorPago" class="error-text">{{ props.errorPago }}</p>

      <button class="btn-confirmar" :disabled="!props.pagoValido" @click="emit('confirmar-venta')">
        Confirmar Venta
      </button>
    </div>
  </div>
</template>

<style scoped>
.ticket-panel {
  border: 1px solid #d8dde6;
  border-radius: 14px;
  background: #fff;
  padding: 16px;
  height: fit-content;
}

@media (min-width: 1081px) {
  .ticket-panel {
    min-height: calc(100vh - 250px);
  }
}

.ticket-panel h3 {
  margin: 0 0 10px;
  font-size: 18px;
  font-weight: 700;
  color: #08324a;
}

.empty-ticket {
  color: #6b7280;
  text-align: center;
  padding: 10px;
}

.ticket-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.ticket-table th,
.ticket-table td {
  border-bottom: 1px solid #e2e8f0;
  padding: 8px 0;
}

.center {
  text-align: center;
}

.right {
  text-align: right;
}

.qty-inline {
  display: flex;
  align-items: center;
  justify-content: center;
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

.qty-current {
  min-width: 18px;
  font-weight: 700;
}

.delete-btn {
  border: none;
  background: none;
  color: #c53030;
  font-weight: 700;
  cursor: pointer;
}

.checkout-box {
  margin-top: 18px;
  border-top: 2px dashed #c7d2e0;
  padding-top: 14px;
}

.total-line {
  display: flex;
  justify-content: space-between;
  font-size: 21px;
  font-weight: 700;
  margin-bottom: 12px;
}

.price-total {
  color: #1f7a3e;
  font-weight: 700;
}

.payment-types {
  display: grid;
  gap: 6px;
  margin-bottom: 12px;
  background: #eef2f6;
  border-radius: 10px;
  padding: 10px;
}

.pay-grid {
  display: grid;
  gap: 10px;
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px;
}

.pay-grid input,
.cuenta-wrap select {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
}

.cuenta-wrap {
  margin-bottom: 12px;
  background: #f8fafc;
  border-radius: 10px;
  padding: 10px;
}

.diff-text {
  color: #b42318;
}

.diff-text.ok {
  color: #1f7a3e;
}

.btn-confirmar {
  width: 100%;
  padding: 12px;
  font-size: 18px;
  background: #1f7a3e;
  color: #fff;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
}

.btn-confirmar:disabled {
  background: #97a3b6;
  cursor: not-allowed;
}

.error-text {
  color: #c53030;
  margin-top: 12px;
  font-weight: 600;
}
</style>
