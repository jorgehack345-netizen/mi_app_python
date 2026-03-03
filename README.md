
# Sistema de Control de Gimnasio (Offline)

Aplicación de consola en **Python** para registrar clientes de un gimnasio, controlar pagos **semanales o mensuales**, y ver **atrasados / vencen hoy / próximos**. Funciona **sin internet** y guarda datos en `data/clientes.json`.

## Estructura
```
mi_gym_app/
├─ app.py
└─ data/
```

## Requisitos
- Tener Python instalado (o usar WinPython portátil en USB).

## Uso
1. Abrir una terminal en la carpeta del proyecto.
2. Ejecutar:
```bash
python app.py
```

## Funciones
- Registrar clientes nuevos
- Listar clientes
- Buscar por nombre
- Ver pendientes de pago
- Cobrar / Renovar (calcula adeudos y actualiza próxima fecha)
- Activar / Inactivar clientes
- Cambiar precios por defecto y configuración
- Exportar CSV

## Notas
- La primera vez que corre, crea `data/clientes.json` automáticamente.
- Formato de fecha aceptado: `dd/mm/aaaa` o `yyyy-mm-dd`.
