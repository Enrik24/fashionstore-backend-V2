#!/bin/bash
# ============================================================
# Script de inicio para FashionStore Backend en Railway
# Migraciones, seed y arranque de la aplicación
# ============================================================

set -e  # Detener si hay algún error

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  FashionStore Backend - Setup & Start  ${NC}"
echo -e "${BLUE}========================================${NC}"

# Detectar puerto (Railway/Render usa $PORT, local usa 8000)
PORT=${PORT:-8000}
echo -e "\n${YELLOW}[INFO] Puerto configurado: $PORT${NC}"
echo -e "${YELLOW}[INFO] Host configurado: 0.0.0.0${NC}"

# ============================================================
# Paso 1: Ejecutar migraciones con Alembic (con timeout)
# ============================================================
echo -e "\n${GREEN}[1/3] Ejecutando migraciones de base de datos...${NC}"

# Función para ejecutar comando con timeout
run_with_timeout() {
    local timeout=$1
    shift
    local command=("$@")
    
    # Ejecutar comando en background
    "${command[@]}" &
    local pid=$!
    
    # Esperar con timeout
    local count=0
    while kill -0 $pid 2>/dev/null; do
        if [ $count -ge $timeout ]; then
            echo -e "${RED}[✗] Timeout alcanzado (${timeout}s)${NC}"
            kill -9 $pid 2>/dev/null || true
            return 1
        fi
        sleep 1
        ((count++))
    done
    
    # Verificar código de salida
    wait $pid
    return $?
}

# Ejecutar migraciones con timeout de 120 segundos
if run_with_timeout 120 alembic upgrade head; then
    echo -e "${GREEN}[✓] Migraciones aplicadas correctamente${NC}"
else
    echo -e "${RED}[✗] Error al aplicar migraciones${NC}"
    exit 1
fi

# ============================================================
# Paso 2: Ejecutar seed de datos iniciales (DESHABILITADO)
# ============================================================
# echo -e "\n${GREEN}[2/3] Ejecutando seed de datos iniciales...${NC}"

# Ejecutar seed con timeout de 60 segundos y manejo de errores
# if run_with_timeout 60 python seed.py; then
#     echo -e "${GREEN}[✓] Seed ejecutado correctamente${NC}"
# else
#     # El seed puede fallar si los datos ya existen, lo cual es aceptable
#     echo -e "${YELLOW}[!] Advertencia: Seed completado con errores (esto es normal si los datos ya existen)${NC}"
# fi

echo -e "\n${YELLOW}[2/3] Seed deshabilitado - ejecutar manualmente si es necesario${NC}"

# ============================================================
# Paso 3: Iniciar la aplicación con Gunicorn
# ============================================================
echo -e "\n${GREEN}[3/3] Iniciando FashionStore API...${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}  API disponible en: http://0.0.0.0:${PORT}${NC}"
echo -e "${BLUE}  Documentación:     http://0.0.0.0:${PORT}/docs${NC}"
echo -e "${BLUE}========================================${NC}\n"

# Verificar que las variables de entorno críticas estén configuradas
if [ -z "$SECRET_KEY" ]; then
    echo -e "${RED}[✗] ERROR: SECRET_KEY no está configurada${NC}"
    exit 1
fi

if [ -z "$DATABASE_URL" ] && [ -z "$DB_HOST" ]; then
    echo -e "${RED}[✗] ERROR: DATABASE_URL o DB_HOST deben estar configuradas${NC}"
    exit 1
fi

echo -e "${GREEN}[✓] Variables de entorno verificadas${NC}\n"

# Debug: Mostrar configuración final
echo -e "${YELLOW}[DEBUG] Configuración final:${NC}"
echo -e "${YELLOW}  - Puerto: ${PORT}${NC}"
echo -e "${YELLOW}  - Workers: 2${NC}"
echo -e "${YELLOW}  - Bind: 0.0.0.0:${PORT}${NC}"
echo -e "${YELLOW}  - Worker class: uvicorn.workers.UvicornWorker${NC}\n"

# Iniciar servidor con exec para que reciba señales correctamente
echo -e "${GREEN}Ejecutando Gunicorn...${NC}\n"
exec gunicorn main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --worker-connections 1000 \
    --timeout 120 \
    --keepalive 5 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload
