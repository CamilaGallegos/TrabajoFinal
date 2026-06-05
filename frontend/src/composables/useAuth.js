import { ref } from 'vue'
import axios from 'axios'

export function useAuth(options = {}) {
  const {
    onLoginSuccess,
    onLogout,
    onSessionExpired,
  } = options

  const dniInput = ref('')
  const isAuthenticated = ref(false)
  const token = ref('')
  const becadoActual = ref(null)
  const errorMensaje = ref('')
  const infoMensaje = ref('')

  let temporizadorSesion = null

  const setAuthToken = (jwtToken) => {
    if (jwtToken) {
      axios.defaults.headers.common.Authorization = `Bearer ${jwtToken}`
    } else {
      delete axios.defaults.headers.common.Authorization
    }
  }

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

  const limpiarTemporizadorSesion = () => {
    if (temporizadorSesion) {
      clearTimeout(temporizadorSesion)
      temporizadorSesion = null
    }
  }

  const cerrarSesion = () => {
    limpiarTemporizadorSesion()
    localStorage.removeItem('sigfo_token')
    localStorage.removeItem('sigfo_becado')
    setAuthToken('')

    token.value = ''
    becadoActual.value = null
    isAuthenticated.value = false
    dniInput.value = ''

    if (onLogout) {
      onLogout()
    }
  }

  const programarCierreSesionPorToken = (jwtToken) => {
    limpiarTemporizadorSesion()

    const payload = decodificarPayloadJWT(jwtToken)
    const exp = payload?.exp
    if (!exp) {
      return false
    }

    const milisegundosRestantes = (exp * 1000) - Date.now()
    if (milisegundosRestantes <= 0) {
      return false
    }

    temporizadorSesion = setTimeout(() => {
      cerrarSesion()
      errorMensaje.value = 'Sesion expirada. Volve a ingresar tu DNI para continuar.'
      infoMensaje.value = ''
      if (onSessionExpired) {
        onSessionExpired()
      }
    }, milisegundosRestantes)

    return true
  }

  const iniciarSesion = async () => {
    errorMensaje.value = ''
    infoMensaje.value = ''

    if (!dniInput.value) {
      errorMensaje.value = 'Por favor, ingresa tu DNI'
      return false
    }

    try {
      const respuesta = await axios.post('http://localhost:8000/api/fichaje/entrada/', {
        dni: dniInput.value,
      })

      token.value = respuesta.data.token
      becadoActual.value = respuesta.data.becado
      infoMensaje.value = respuesta.data.msg
      isAuthenticated.value = true
      setAuthToken(token.value)
      programarCierreSesionPorToken(token.value)

      localStorage.setItem('sigfo_token', token.value)
      localStorage.setItem('sigfo_becado', JSON.stringify(becadoActual.value))

      if (onLoginSuccess) {
        await onLoginSuccess()
      }

      return true
    } catch (error) {
      if (error.response && error.response.status === 404) {
        errorMensaje.value = 'El DNI ingresado no corresponde a un becado/a activo/a.'
      } else {
        errorMensaje.value = 'Error al iniciar sesión. Por favor, intenta nuevamente.'
      }
      return false
    }
  }

  const restaurarSesion = async () => {
    const tokenGuardado = localStorage.getItem('sigfo_token')
    const becadoGuardado = localStorage.getItem('sigfo_becado')

    if (!tokenGuardado || !becadoGuardado) {
      return false
    }

    if (!programarCierreSesionPorToken(tokenGuardado)) {
      cerrarSesion()
      errorMensaje.value = 'Sesion expirada. Volve a ingresar tu DNI para continuar.'
      if (onSessionExpired) {
        onSessionExpired()
      }
      return false
    }

    token.value = tokenGuardado
    setAuthToken(token.value)
    becadoActual.value = JSON.parse(becadoGuardado)
    isAuthenticated.value = true

    if (onLoginSuccess) {
      await onLoginSuccess()
    }

    return true
  }

  return {
    dniInput,
    isAuthenticated,
    token,
    becadoActual,
    errorMensaje,
    infoMensaje,
    iniciarSesion,
    cerrarSesion,
    restaurarSesion,
  }
}
