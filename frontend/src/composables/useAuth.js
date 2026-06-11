import { computed, ref } from 'vue'
import axios from 'axios'

export function useAuth(options = {}) {
  const { onLoginSuccess, onLogout, onSessionExpired } = options

  const STORAGE_SESIONES = 'sigfo_sesiones'

  const dniInput = ref('')
  const sesionesActivas = ref([])
  const sesionActivaId = ref(null)
  const isAuthenticated = computed(() => sesionesActivas.value.length > 0)
  const token = ref('')
  const becadoActual = computed(() => {
    return sesionesActivas.value.find((sesion) => sesion.id === sesionActivaId.value)?.becado || null
  })
  const becadosActivos = computed(() => sesionesActivas.value.map((sesion) => sesion.becado))
  const errorMensaje = ref('')
  const infoMensaje = ref('')

  const timersPorSesion = new Map()

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

  const guardarSesiones = () => {
    const payload = sesionesActivas.value.map((sesion) => ({
      id: sesion.id,
      token: sesion.token,
      becado: sesion.becado,
      msg: sesion.msg || '',
    }))
    localStorage.setItem(STORAGE_SESIONES, JSON.stringify(payload))
  }

  const aplicarAuthDeSesionActiva = () => {
    const sesion = sesionesActivas.value.find((item) => item.id === sesionActivaId.value)
    if (!sesion) {
      token.value = ''
      setAuthToken('')
      return
    }
    token.value = sesion.token
    setAuthToken(sesion.token)
  }

  const limpiarTimerSesion = (idSesion) => {
    const timer = timersPorSesion.get(idSesion)
    if (timer) {
      clearTimeout(timer)
      timersPorSesion.delete(idSesion)
    }
  }

  const limpiarTodosLosTimers = () => {
    timersPorSesion.forEach((timer) => clearTimeout(timer))
    timersPorSesion.clear()
  }

  const cerrarSesionPorId = (idSesion, { expirada = false } = {}) => {
    limpiarTimerSesion(idSesion)
    sesionesActivas.value = sesionesActivas.value.filter((sesion) => sesion.id !== idSesion)

    if (sesionesActivas.value.length === 0) {
      sesionActivaId.value = null
      token.value = ''
      setAuthToken('')
      localStorage.removeItem('sigfo_token')
      localStorage.removeItem('sigfo_becado')
      localStorage.removeItem(STORAGE_SESIONES)
      dniInput.value = ''
      if (expirada) {
        errorMensaje.value = 'Una sesion expiro. Vuelve a ingresar DNI para continuar.'
      }
      if (onLogout) {
        onLogout()
      }
      return
    }

    if (!sesionesActivas.value.some((sesion) => sesion.id === sesionActivaId.value)) {
      sesionActivaId.value = sesionesActivas.value[0].id
      infoMensaje.value = `Sesion activa: ${sesionesActivas.value[0].becado.nombre}`
    }

    aplicarAuthDeSesionActiva()
    guardarSesiones()
  }

  const cerrarSesion = () => {
    if (!sesionActivaId.value) {
      return
    }
    cerrarSesionPorId(sesionActivaId.value)
  }

  const cerrarTodasLasSesiones = () => {
    limpiarTodosLosTimers()
    sesionesActivas.value = []
    sesionActivaId.value = null
    token.value = ''
    setAuthToken('')
    dniInput.value = ''
    localStorage.removeItem('sigfo_token')
    localStorage.removeItem('sigfo_becado')
    localStorage.removeItem(STORAGE_SESIONES)
    if (onLogout) {
      onLogout()
    }
  }

  const programarCierreSesionPorToken = (idSesion, jwtToken) => {
    limpiarTimerSesion(idSesion)

    const payload = decodificarPayloadJWT(jwtToken)
    const exp = payload?.exp
    if (!exp) {
      return false
    }

    const milisegundosRestantes = (exp * 1000) - Date.now()
    if (milisegundosRestantes <= 0) {
      return false
    }

    const nuevoTimer = setTimeout(() => {
      const sesionExpirada = sesionesActivas.value.find((sesion) => sesion.id === idSesion)
      if (!sesionExpirada) {
        return
      }

      cerrarSesionPorId(idSesion, { expirada: true })
      infoMensaje.value = ''
      if (onSessionExpired) {
        onSessionExpired(sesionExpirada.becado)
      }
    }, milisegundosRestantes)

    timersPorSesion.set(idSesion, nuevoTimer)
    return true
  }

  const seleccionarSesionActiva = (idSesion) => {
    if (!sesionesActivas.value.some((sesion) => sesion.id === idSesion)) {
      return false
    }
    sesionActivaId.value = idSesion
    aplicarAuthDeSesionActiva()
    const sesion = sesionesActivas.value.find((item) => item.id === idSesion)
    if (sesion) {
      infoMensaje.value = `Sesion activa: ${sesion.becado.nombre}`
    }
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

      const idSesion = String(respuesta.data.becado.id)
      const tokenNuevo = respuesta.data.token
      const sesionExistente = sesionesActivas.value.find((sesion) => sesion.id === idSesion)

      if (sesionExistente) {
        sesionExistente.token = tokenNuevo
        sesionExistente.msg = respuesta.data.msg
      } else {
        sesionesActivas.value.push({
          id: idSesion,
          token: tokenNuevo,
          becado: respuesta.data.becado,
          msg: respuesta.data.msg,
        })
      }

      sesionActivaId.value = idSesion
      infoMensaje.value = respuesta.data.msg
      aplicarAuthDeSesionActiva()
      programarCierreSesionPorToken(idSesion, tokenNuevo)
      guardarSesiones()

      localStorage.setItem('sigfo_token', tokenNuevo)
      localStorage.setItem('sigfo_becado', JSON.stringify(respuesta.data.becado))
      dniInput.value = ''

      if (onLoginSuccess) {
        await onLoginSuccess()
      }

      return true
    } catch (error) {
      if (error.response && error.response.status === 404) {
        errorMensaje.value = 'El DNI ingresado no corresponde a un becado/a activo/a.'
      } else {
        errorMensaje.value = 'Error al iniciar sesion. Por favor, intenta nuevamente.'
      }
      return false
    }
  }

  const restaurarSesion = async () => {
    const sesionesGuardadasRaw = localStorage.getItem(STORAGE_SESIONES)

    if (sesionesGuardadasRaw) {
      try {
        const sesionesGuardadas = JSON.parse(sesionesGuardadasRaw)
        if (Array.isArray(sesionesGuardadas)) {
          const sesionesValidas = []

          for (const sesion of sesionesGuardadas) {
            if (!sesion?.id || !sesion?.token || !sesion?.becado) {
              continue
            }
            if (!programarCierreSesionPorToken(String(sesion.id), sesion.token)) {
              continue
            }
            sesionesValidas.push({
              id: String(sesion.id),
              token: sesion.token,
              becado: sesion.becado,
              msg: sesion.msg || '',
            })
          }

          sesionesActivas.value = sesionesValidas
          if (sesionesActivas.value.length > 0) {
            sesionActivaId.value = sesionesActivas.value[0].id
            aplicarAuthDeSesionActiva()
            if (onLoginSuccess) {
              await onLoginSuccess()
            }
            guardarSesiones()
            return true
          }
        }
      } catch {
        localStorage.removeItem(STORAGE_SESIONES)
      }
    }

    const tokenGuardado = localStorage.getItem('sigfo_token')
    const becadoGuardado = localStorage.getItem('sigfo_becado')

    if (!tokenGuardado || !becadoGuardado) {
      return false
    }

    const becado = JSON.parse(becadoGuardado)
    const idSesion = String(becado.id)

    if (!programarCierreSesionPorToken(idSesion, tokenGuardado)) {
      cerrarTodasLasSesiones()
      errorMensaje.value = 'Sesion expirada. Vuelve a ingresar DNI para continuar.'
      return false
    }

    sesionesActivas.value = [{
      id: idSesion,
      token: tokenGuardado,
      becado,
      msg: '',
    }]
    sesionActivaId.value = idSesion
    aplicarAuthDeSesionActiva()
    guardarSesiones()

    if (onLoginSuccess) {
      await onLoginSuccess()
    }

    return true
  }

  return {
    dniInput,
    sesionesActivas,
    becadosActivos,
    sesionActivaId,
    isAuthenticated,
    token,
    becadoActual,
    errorMensaje,
    infoMensaje,
    iniciarSesion,
    cerrarSesion,
    cerrarTodasLasSesiones,
    seleccionarSesionActiva,
    restaurarSesion,
  }
}
