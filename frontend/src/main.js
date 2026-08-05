import { createApp } from 'vue'
import axios from 'axios'
import VueApexCharts from 'vue3-apexcharts'
import './style.css'
import App from './App.vue'
import router from './router'
import {
	STORAGE_KEYS,
	limpiarAuthPersistida,
	normalizarSesionesValidas,
	seleccionarSesionPersistida,
	tokenExpirado,
} from './utils/authSession'

const limpiarAuthGlobal = () => {
	limpiarAuthPersistida()
	delete axios.defaults.headers.common.Authorization
}

// al recargar la app, restaura el token guardado en localStorage y lo setea en axios para que las primeras requests salgan autenticadas
const restaurarAuthPersistida = () => {
	const sesionesValidas = normalizarSesionesValidas()
	if (sesionesValidas.length > 0) {
		const sesionElegida = seleccionarSesionPersistida(sesionesValidas)
		if (sesionElegida?.token) {
			axios.defaults.headers.common.Authorization = `Bearer ${sesionElegida.token}`
			localStorage.setItem(STORAGE_KEYS.token, sesionElegida.token)
			localStorage.setItem(STORAGE_KEYS.becado, JSON.stringify(sesionElegida.becado || {}))
			return
		}

		limpiarAuthGlobal()
		return
	}

	const tokenGuardado = localStorage.getItem(STORAGE_KEYS.token)
	if (tokenGuardado) {
		if (tokenExpirado(tokenGuardado)) {
			limpiarAuthGlobal()
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
