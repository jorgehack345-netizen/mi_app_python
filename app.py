import os
import json
import csv
from datetime import datetime, date, timedelta

# =========================
# Configuración y utilitarios
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_FILE = os.path.join(DATA_DIR, "clientes.json")
DATE_FMT_SHOW = "%d/%m/%Y"   # Para mostrar al usuario (día/mes/año)
DATE_FMT_STORE = "%Y-%m-%d"  # Para guardar en JSON (ISO simple)

DEFAULT_CONFIG = {
    "precio_semanal": 120.0,   # cámbialo en el menú [7]
    "precio_mensual": 450.0,   # cámbialo en el menú [7]
    "dias_proximos": 7         # horizonte para "próximos vencimientos"
}

# =========================
# Manejo de fechas
# =========================

def hoy() -> date:
    return date.today()

def parse_date_input(s: str) -> date:
    """
    Acepta 'dd/mm/yyyy' o 'yyyy-mm-dd'.
    """
    s = s.strip()
    for fmt in (DATE_FMT_SHOW, DATE_FMT_STORE):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    raise ValueError("Formato de fecha inválido. Usa dd/mm/aaaa o yyyy-mm-dd.")

def fmt_show(d: date) -> str:
    return d.strftime(DATE_FMT_SHOW)

def add_months(d: date, months: int) -> date:
    """
    Suma meses respetando fin de mes (sin librerías externas).
    """
    y = d.year + (d.month - 1 + months) // 12
    m = (d.month - 1 + months) % 12 + 1
    # Determinar último día del mes destino
    last_day = (date(y, m, 1) + timedelta(days=31)).replace(day=1) - timedelta(days=1)
    day = min(d.day, last_day.day)
    return date(y, m, day)

def next_due(fecha_inicio: date, plan: str) -> date:
    """
    Calcula la próxima fecha de pago desde la fecha de inicio (o última renovación).
    """
    if plan == "semanal":
        return fecha_inicio + timedelta(weeks=1)
    elif plan == "mensual":
        return add_months(fecha_inicio, 1)
    else:
        raise ValueError("Plan desconocido.")

def avanzar_hasta_ponerse_al_corriente(due: date, plan: str, ref: date) -> (date, int):
    """
    Avanza la fecha 'due' sumando periodos hasta que sea > ref (hoy),
    devolviendo la nueva fecha y cuántos periodos se acumularon (adeudo).
    Si due > ref, periodos = 0.
    """
    periodos = 0
    current = due
    while current <= ref:
        periodos += 1
        if plan == "semanal":
            current = current + timedelta(weeks=1)
        else:
            current = add_months(current, 1)
    return current, periodos

# =========================
# Base de datos (JSON)
# =========================

def ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)

def load_db():
    ensure_dirs()
    if not os.path.exists(DB_FILE):
        data = {
            "configs": DEFAULT_CONFIG.copy(),
            "clientes": []
        }
        save_db(data)
        return data
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def next_id(clientes):
    if not clientes:
        return 1
    return max(c["id"] for c in clientes) + 1

# =========================
# Funciones de negocio
# =========================

def registrar_cliente(data):
    cfg = data["configs"]
    clientes = data["clientes"]

    print("\n=== Registrar cliente nuevo ===")
    nombre = input("Nombre del cliente: ").strip()
    if not nombre:
        print("El nombre no puede estar vacío.")
        return

    # Plan
    plan = ""
    while plan not in ("semanal", "mensual"):
        plan = input("Plan (semanal/mensual): ").strip().lower()
        if plan not in ("semanal", "mensual"):
            print("Opción inválida. Escribe 'semanal' o 'mensual'.")

    # Precio (por cliente) — por defecto tomamos de configs, pero puedes personalizar
    default_precio = cfg["precio_semanal"] if plan == "semanal" else cfg["precio_mensual"]
    precio_in = input(f"Precio ({default_precio} por defecto): ").strip()
    if precio_in == "":
        precio = float(default_precio)
    else:
        try:
            precio = float(precio_in)
        except ValueError:
            print("Precio inválido. Se usará el precio por defecto.")
            precio = float(default_precio)

    # Fecha de inicio
    print("Fecha de inicio (enter para hoy) — formato dd/mm/aaaa:")
    fin_in = input("> ").strip()
    if fin_in == "":
        f_inicio = hoy()
    else:
        try:
            f_inicio = parse_date_input(fin_in)
        except ValueError as e:
            print(str(e), "Se usará la fecha de hoy.")
            f_inicio = hoy()

    f_due = next_due(f_inicio, plan)

    cliente = {
        "id": next_id(clientes),
        "nombre": nombre,
        "plan": plan,
        "precio": precio,
        "fecha_alta": f_inicio.strftime(DATE_FMT_STORE),
        "proximo_pago": f_due.strftime(DATE_FMT_STORE),
        "activo": True,
        "ultima_renovacion": None
    }
    clientes.append(cliente)
    save_db(data)
    print(f"\nCliente registrado con ID {cliente['id']}. Próximo pago: {fmt_show(f_due)}")

def listar_clientes(data):
    print("\n=== Lista de clientes ===")
    clientes = data["clientes"]
    if not clientes:
        print("(No hay clientes)")
        return
    for c in clientes:
        f_due = datetime.strptime(c["proximo_pago"], DATE_FMT_STORE).date()
        estado = "ACTIVO" if c.get("activo", True) else "INACTIVO"
        print(f"- ID {c['id']:>3} | {c['nombre']:<25} | {c['plan']:<7} | ${c['precio']:<8.2f} | Próximo: {fmt_show(f_due)} | {estado}")

def buscar_cliente_por_nombre(data):
    q = input("\nBuscar por nombre (texto): ").strip().lower()
    encontrados = [c for c in data["clientes"] if q in c["nombre"].lower()]
    if not encontrados:
        print("No se encontraron coincidencias.")
        return []
    print(f"\nCoincidencias ({len(encontrados)}):")
    for c in encontrados:
        f_due = datetime.strptime(c["proximo_pago"], DATE_FMT_STORE).date()
        print(f"- ID {c['id']:>3} | {c['nombre']} | Plan: {c['plan']} | Próximo: {fmt_show(f_due)}")
    return encontrados

def seleccionar_cliente_por_id(data):
    try:
        cid = int(input("Ingresa el ID del cliente: ").strip())
    except ValueError:
        print("ID inválido.")
        return None
    for c in data["clientes"]:
        if c["id"] == cid:
            return c
    print("No existe un cliente con ese ID.")
    return None

def ver_pendientes(data):
    cfg = data["configs"]
    dias_proximos = int(cfg.get("dias_proximos", 7))
    print("\n=== Pendientes de pago ===")
    hoy_d = hoy()
    prox_limite = hoy_d + timedelta(days=dias_proximos)

    atrasados = []
    hoy_list = []
    proximos = []

    for c in data["clientes"]:
        if not c.get("activo", True):
            continue
        due = datetime.strptime(c["proximo_pago"], DATE_FMT_STORE).date()
        if due < hoy_d:
            atrasados.append(c)
        elif due == hoy_d:
            hoy_list.append(c)
        elif hoy_d < due <= prox_limite:
            proximos.append(c)

    def _print_list(titulo, lst):
        print(f"\n{titulo} ({len(lst)}):")
        if not lst:
            print("  (ninguno)")
        for c in lst:
            due = datetime.strptime(c["proximo_pago"], DATE_FMT_STORE).date()
            print(f"  - ID {c['id']:>3} | {c['nombre']:<25} | {c['plan']:<7} | ${c['precio']:<8.2f} | Vence: {fmt_show(due)}")

    _print_list("Atrasados", atrasados)
    _print_list("Vencen hoy", hoy_list)
    _print_list(f"Próximos {dias_proximos} días", proximos)

def cobrar_renovar(data):
    print("\n=== Cobrar / Renovar ===")
    # Permite buscar por nombre o ir directo por ID
    op = input("¿Buscar por (n)ombre o (i)D? [n/i]: ").strip().lower()
    cliente = None
    if op == "n":
        resultados = buscar_cliente_por_nombre(data)
        if resultados:
            cliente = seleccionar_cliente_por_id(data)
    else:
        cliente = seleccionar_cliente_por_id(data)

    if not cliente:
        return

    if not cliente.get("activo", True):
        print("Este cliente está INACTIVO. Actívalo antes de cobrar.")
        return

    plan = cliente["plan"]
    precio = float(cliente["precio"])
    due = datetime.strptime(cliente["proximo_pago"], DATE_FMT_STORE).date()
    hoy_d = hoy()

    # ¿Cuántos periodos debe?
    if due > hoy_d:
        periodos = 1  # Renovación por el siguiente periodo
        nuevo_due = next_due(due, plan) if plan == "semanal" else add_months(due, 1)
        mensaje = "No está atrasado. Renovación por el siguiente periodo."
    else:
        # Atrasado o vence hoy: avanzar hasta ponerse al corriente (+1 periodo para renovar)
        nuevo_due_temp, adeudo = avanzar_hasta_ponerse_al_corriente(due, plan, hoy_d)
        periodos = adeudo  # Solo los adeudados (para ponerse al corriente)
        nuevo_due = nuevo_due_temp
        mensaje = f"Adeuda {adeudo} periodo(s)."

    monto = precio * periodos

    print("\nResumen de cobro:")
    print(f"- Cliente: {cliente['nombre']} (ID {cliente['id']})")
    print(f"- Plan: {plan} | Precio por periodo: ${precio:.2f}")
    print(f"- {mensaje}")
    print(f"- Monto a cobrar ahora: ${monto:.2f}")
    print(f"- Próxima fecha de pago tras cobro: {fmt_show(nuevo_due)}")

    conf = input("¿Confirmar cobro? (s/n): ").strip().lower()
    if conf == "s":
        cliente["proximo_pago"] = nuevo_due.strftime(DATE_FMT_STORE)
        cliente["ultima_renovacion"] = hoy_d.strftime(DATE_FMT_STORE)
        save_db(data)
        print("✅ Cobro registrado y próxima fecha actualizada.")
    else:
        print("Operación cancelada.")

def cambiar_precios_por_defecto(data):
    cfg = data["configs"]
    print("\n=== Cambiar precios por defecto ===")
    print(f"Precio semanal actual: ${cfg['precio_semanal']:.2f}")
    print(f"Precio mensual actual: ${cfg['precio_mensual']:.2f}")
    print(f"Días para 'próximos vencimientos' (actual): {cfg['dias_proximos']}")

    ps = input("Nuevo precio semanal (enter para dejar igual): ").strip()
    pm = input("Nuevo precio mensual (enter para dejar igual): ").strip()
    dp = input("Nuevo horizonte de próximos vencimientos en días (enter para igual): ").strip()

    if ps != "":
        try:
            cfg["precio_semanal"] = float(ps)
        except ValueError:
            print("Valor inválido para semanal. Se conserva el actual.")
    if pm != "":
        try:
            cfg["precio_mensual"] = float(pm)
        except ValueError:
            print("Valor inválido para mensual. Se conserva el actual.")
    if dp != "":
        try:
            cfg["dias_proximos"] = int(dp)
        except ValueError:
            print("Valor inválido para días. Se conserva el actual.")

    save_db(data)
    print("✅ Configuración actualizada.")

def activar_inactivar_cliente(data):
    print("\n=== Activar / Inactivar cliente ===")
    cliente = seleccionar_cliente_por_id(data)
    if not cliente:
        return
    estado_actual = cliente.get("activo", True)
    print(f"Estado actual: {'ACTIVO' if estado_actual else 'INACTIVO'}")
    nuevo = input("¿Marcar como (a)ctivo o (i)nactivo? [a/i]: ").strip().lower()
    if nuevo == "a":
        cliente["activo"] = True
    elif nuevo == "i":
        cliente["activo"] = False
    else:
        print("Opción inválida.")
        return
    save_db(data)
    print("✅ Estado actualizado.")

def exportar_csv(data):
    print("\n=== Exportar CSV ===")
    out_file = os.path.join(DATA_DIR, "reporte_clientes.csv")
    campos = ["id", "nombre", "plan", "precio", "fecha_alta", "proximo_pago", "activo", "ultima_renovacion"]
    with open(out_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=campos)
        writer.writeheader()
        for c in data["clientes"]:
            writer.writerow(c)
    print(f"✅ Archivo creado: {out_file}")

# =========================
# Menú principal
# =========================

def menu():
    data = load_db()
    while True:
        print("\n" + "="*50)
        print(" GESTIÓN DE GIMNASIO - APP OFFLINE ")
        print("="*50)
        print("1) Registrar cliente nuevo")
        print("2) Listar clientes")
        print("3) Buscar cliente por nombre")
        print("4) Ver pendientes de pago (atrasados / hoy / próximos)")
        print("5) Cobrar / Renovar")
        print("6) Activar / Inactivar cliente")
        print("7) Cambiar precios por defecto y configuración")
        print("8) Exportar CSV")
        print("9) Salir")
        op = input("Elige una opción: ").strip()

        if op == "1":
            registrar_cliente(data)
        elif op == "2":
            listar_clientes(data)
        elif op == "3":
            buscar_cliente_por_nombre(data)
        elif op == "4":
            ver_pendientes(data)
        elif op == "5":
            cobrar_renovar(data)
        elif op == "6":
            activar_inactivar_cliente(data)
        elif op == "7":
            cambiar_precios_por_defecto(data)
        elif op == "8":
            exportar_csv(data)
        elif op == "9":
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida. Intenta de nuevo.")

if __name__ == "__main__":
    menu()
