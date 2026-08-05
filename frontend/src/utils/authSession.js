export const STORAGE_KEYS = {
  token: 'sigfo_token',
  becado: 'sigfo_becado',
  role: 'sigfo_role',
  sesiones: 'sigfo_sesiones',
}

export const decodificarPayloadJWT = (jwtToken) => {
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

export const tokenExpirado = (jwtToken) => {
  const payload = decodificarPayloadJWT(jwtToken)
  const exp = payload?.exp
  if (!exp) {
    return true
  }
  return (exp * 1000) <= Date.now()
}

export const limpiarAuthPersistida = () => {
  localStorage.removeItem(STORAGE_KEYS.token)
  localStorage.removeItem(STORAGE_KEYS.becado)
  localStorage.removeItem(STORAGE_KEYS.role)
  localStorage.removeItem(STORAGE_KEYS.sesiones)
}

export const normalizarSesionesValidas = () => {
  const sesionesRaw = localStorage.getItem(STORAGE_KEYS.sesiones)
  if (!sesionesRaw) {
    return []
  }

  try {
    const sesiones = JSON.parse(sesionesRaw)
    if (!Array.isArray(sesiones)) {
      return []
    }

    const validas = sesiones.filter((sesion) => sesion?.token && !tokenExpirado(sesion.token))
    if (validas.length !== sesiones.length) {
      if (validas.length > 0) {
        localStorage.setItem(STORAGE_KEYS.sesiones, JSON.stringify(validas))
      } else {
        localStorage.removeItem(STORAGE_KEYS.sesiones)
      }
    }

    return validas
  } catch {
    localStorage.removeItem(STORAGE_KEYS.sesiones)
    return []
  }
}

export const obtenerRolGuardado = () => {
  if (localStorage.getItem(STORAGE_KEYS.role) === 'admin') {
    return 'admin'
  }

  const sesionesRaw = localStorage.getItem(STORAGE_KEYS.sesiones)
  if (sesionesRaw) {
    try {
      const sesiones = JSON.parse(sesionesRaw)
      if (Array.isArray(sesiones)) {
        const sesionAdmin = sesiones.find((sesion) => sesion.role === 'admin' || sesion.isAdmin)
        if (sesionAdmin) {
          return 'admin'
        }
      }
    } catch {
    }
  }

  return 'becado'
}

export const seleccionarSesionPersistida = (sesionesValidas) => {
  if (!Array.isArray(sesionesValidas) || sesionesValidas.length === 0) {
    return null
  }

  const adminMode = localStorage.getItem(STORAGE_KEYS.role) === 'admin'
  const sesionAdmin = sesionesValidas.find((s) => (s?.role === 'admin' || s?.isAdmin) && s?.token)
  const sesionFallback = sesionesValidas.find((s) => s?.token)

  return adminMode ? (sesionAdmin || sesionFallback || null) : (sesionFallback || null)
}
