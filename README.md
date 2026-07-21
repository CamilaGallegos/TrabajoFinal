# TrabajoFinal
SiGFo CURZAS (Sistema de Gestión de la Fotocopiadora del CURZAS)

📝 Descripción del Proyecto
Este sistema está diseñado para la automatizacion de la gestión de la fotocopiadora de nuestra sede universitaria que es operada de manera autogestiva por estudiantes becados. El objetivo es centralizar y agilizar el registro de ventas de artículos de librería, servicios de impresión/fotocopiado y el control de cuentas abierta departamentales, además de automatizar el seguimiento de horas de los becados, el mantenimiento de maquinaria y estadista de datos.

👥 Roles del Sistema
1. Rol Becado
Asistencia: Fichaje de entrada y salida mediante DNI.
            Soporte para múltiples sesiones activas en una misma terminal (Trabajan al menos 2 becados por turno). 
Venta: Registro rápido de fotocopias (BN, Color, DNI, Escaneo) con variantes Simple/Doble faz indicando cantidad. 
       Módulo de anillados y artículos de librería.  
       Cálculo automático del total. 
       Gestión de metodo de pago (Efectivo o transferencia) incluyendo el caso de pago combinado. 
       Cuentas abiertas: Cada departamento y secretaria de la universidad tiene una cuenta abierta donde se va acomulando fotocopias sacadas por cuatrimestre. 
       Historial de Ventas: Visualización y edición controlada de ventas recientes con auditoría de cambios. 
       
2. Rol Administrador 
Gestión de Usuarios: Control de becados y asistencias. 
Inventario y Precios: Alta, baja y modificación de stock y lista de precios. 
Reportes y Estadísticas: Balances de ingresos y egresos, ranking productos más vendidos y franjas horarias de mayor demanda.
Exportación de datos de las cuentas abiertas (PDF/Excel).

# Diagrama Entidad-Relacion.

Este diseño del modelo de datos prioriza la agilidad de registrar una venta mediante la jerarquía de Categorías y Productos, permitiendo que el becado navegue rápidamente por el catálogo de librería y servicios mientras el sistema realiza el cálculo del total automáticamente. También garantiza el control de errores al registrar cada corrección manual del historial de ventas mediante la tabla auditoria_ventas, donde se guarda el valor anterior y el nuevo para no perder el rastro del dinero.

Para manejar las Cuentas Abiertas, se agregó la columna id_cuenta_abierta en la tabla Venta. Esto permite vincular una venta a un departamento específico solo cuando el pago no es inmediato, logrando así separar el efectivo del día de los consumos acumulados y permitiendo generar los reportes de deuda cuatrimestrales de forma aut
<img width="1180" height="791" alt="image" src="https://github.com/user-attachments/assets/e934c38c-64b8-43d7-8e24-2c4c1918ffa2" />
