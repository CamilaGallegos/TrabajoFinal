<script setup>
import { useRouter } from 'vue-router'

const router = useRouter()

const volverAlPanel = () => {
  router.push({ name: 'panel' })
}
</script>

<template>
  <div class="admin-shell">
    <div class="admin-card">
      <p class="admin-eyebrow">Panel de administración</p>
      <button type="button" class="btn-primary" @click="volverAlPanel">
        Volver al panel de ventas
      </button>
    </div>
  </div>
</template>

<style scoped>
.admin-shell {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
  background: linear-gradient(135deg, #f4f8fc 0%, #e6f2fb 100%);
}

.admin-card {
  width: min(560px, 100%);
  background: #fff;
  border-radius: 18px;
  padding: 28px;
  box-shadow: 0 16px 40px rgba(5, 120, 175, 0.16);
}

.admin-eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: #0578af;
}

h1 {
  margin: 0 0 10px;
  color: #08324a;
}

p {
  color: #475569;
  margin: 0 0 18px;
}

.btn-primary {
  border: none;
  border-radius: 10px;
  cursor: pointer;
  font-weight: 700;
  padding: 10px 14px;
  background: #0578af;
  color: #fff;
}
</style>
