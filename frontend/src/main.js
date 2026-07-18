import { createApp } from 'vue'
import axios from 'axios'
import VueApexCharts from 'vue3-apexcharts'
import './style.css'
import App from './App.vue'
import router from './router'

// al recargar la app, restaura el token guardado en localStorage y lo setea en axios para que las primeras requests salgan autenticadas
const restaurarAuthPersistida = () => {
	const sesionesRaw = localStorage.getItem('sigfo_sesiones')
	if (sesionesRaw) {
		try {
			const sesiones = JSON.parse(sesionesRaw)
			if (Array.isArray(sesiones) && sesiones.length > 0) {
				const adminMode = localStorage.getItem('sigfo_role') === 'admin'
				const sesionAdmin = sesiones.find((s) => (s?.role === 'admin' || s?.isAdmin) && s?.token)
				const sesionFallback = sesiones.find((s) => s?.token)
				const sesionElegida = adminMode ? (sesionAdmin || sesionFallback) : sesionFallback

				if (sesionElegida?.token) {
					axios.defaults.headers.common.Authorization = `Bearer ${sesionElegida.token}`
					return
				}
			}
		} catch {
		}
	}

	const tokenGuardado = localStorage.getItem('sigfo_token')
	if (tokenGuardado) {
		axios.defaults.headers.common.Authorization = `Bearer ${tokenGuardado}`
	}
}

restaurarAuthPersistida()

const app = createApp(App)
app.use(router)
app.component('apexchart', VueApexCharts)
app.mount('#app')
