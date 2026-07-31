import { createApp } from 'vue'
import axios from 'axios'
import VueApexCharts from 'vue3-apexcharts'
import './style.css'
import App from './App.vue'
import router from './router'

const decodificarPayloadJWT = (jwtToken) => {
	try {
		const payloadBase64 = jwtToken.split('.')[1]
		const payloadNormalizado = payloadBase64.replace(/-/g, '+').replace(/_/g, '/')
		const payloadJson = decodeURIComponent(
			atob(payloadNormalizado)
				.split('')
				.map((c) => `%${c.charCodeAt(0).toString(16).padStart(2, '0')}`)
				.join('')
		)
		return JSON.parse(payloadJson)
	} catch {
		return null
	}
}

const tokenExpirado = (jwtToken) => {
	const payload = decodificarPayloadJWT(jwtToken)
	const exp = payload?.exp
	if (!exp) {
		return true
	}
	return (exp * 1000) <= Date.now()
}

const limpiarAuthPersistida = () => {
	localStorage.removeItem('sigfo_token')
	localStorage.removeItem('sigfo_becado')
	localStorage.removeItem('sigfo_role')
	localStorage.removeItem('sigfo_sesiones')
	delete axios.defaults.headers.common.Authorization
}

// al recargar la app, restaura el token guardado en localStorage y lo setea en axios para que las primeras requests salgan autenticadas
const restaurarAuthPersistida = () => {
	const sesionesRaw = localStorage.getItem('sigfo_sesiones')
	if (sesionesRaw) {
		try {
			const sesiones = JSON.parse(sesionesRaw)
			if (Array.isArray(sesiones) && sesiones.length > 0) {
				const sesionesValidas = sesiones.filter((s) => s?.token && !tokenExpirado(s.token))
				if (sesionesValidas.length !== sesiones.length) {
					if (sesionesValidas.length > 0) {
						localStorage.setItem('sigfo_sesiones', JSON.stringify(sesionesValidas))
					} else {
						localStorage.removeItem('sigfo_sesiones')
					}
				}

				if (sesionesValidas.length === 0) {
					limpiarAuthPersistida()
					return
				}

				const adminMode = localStorage.getItem('sigfo_role') === 'admin'
				const sesionAdmin = sesionesValidas.find((s) => (s?.role === 'admin' || s?.isAdmin) && s?.token)
				const sesionFallback = sesionesValidas.find((s) => s?.token)
				const sesionElegida = adminMode ? (sesionAdmin || sesionFallback) : sesionFallback

				if (sesionElegida?.token) {
					axios.defaults.headers.common.Authorization = `Bearer ${sesionElegida.token}`
					localStorage.setItem('sigfo_token', sesionElegida.token)
					localStorage.setItem('sigfo_becado', JSON.stringify(sesionElegida.becado || {}))
					return
				}
			}
		} catch {
			localStorage.removeItem('sigfo_sesiones')
		}
	}

	const tokenGuardado = localStorage.getItem('sigfo_token')
	if (tokenGuardado) {
		if (tokenExpirado(tokenGuardado)) {
			limpiarAuthPersistida()
			return
		}
		axios.defaults.headers.common.Authorization = `Bearer ${tokenGuardado}`
	}
}

restaurarAuthPersistida()

const app = createApp(App)
app.use(router)
app.component('apexchart', VueApexCharts)
app.mount('#app')
