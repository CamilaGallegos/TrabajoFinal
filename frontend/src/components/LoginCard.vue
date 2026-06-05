<script setup>
const props = defineProps({
  dniInput: {
    type: String,
    required: true,
  },
  errorMensaje: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:dniInput', 'iniciar-sesion'])

const onInput = (event) => {
  emit('update:dniInput', event.target.value)
}

const onIniciar = () => {
  emit('iniciar-sesion')
}
</script>

<template>
  <div class="login-card">
    <h2>SiGFo - Acceso</h2>
    <p class="muted">Ingresa tu DNI para fichar tu asistencia e iniciar sesion</p>

    <div class="login-input-wrap">
      <input
        :value="props.dniInput"
        type="text"
        placeholder="Ej: 12345678"
        class="login-input"
        @input="onInput"
        @keyup.enter="onIniciar"
      />
    </div>

    <button class="btn-primary" @click="onIniciar">Ingresar</button>
    <p v-if="props.errorMensaje" class="error-text">{{ props.errorMensaje }}</p>
  </div>
</template>

<style scoped>
.login-card {
  border: 1px solid #d6dbe3;
  padding: 40px;
  border-radius: 16px;
  text-align: center;
  margin-top: 60px;
  background: linear-gradient(180deg, #ffffff, #f7fafc);
}

.muted {
  color: #64748b;
}

.login-input-wrap {
  margin: 20px 0;
}

.login-input {
  padding: 12px;
  width: 260px;
  font-size: 16px;
  text-align: center;
  border-radius: 10px;
  border: 1px solid #b9c3d1;
}

.btn-primary {
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 600;
  padding: 12px 24px;
  font-size: 16px;
  background: #1f7a3e;
  color: #fff;
}

.error-text {
  color: #c53030;
  margin-top: 12px;
  font-weight: 600;
}
</style>
