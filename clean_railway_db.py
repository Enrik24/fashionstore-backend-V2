#!/usr/bin/env python3
"""
Script para limpiar la base de datos PostgreSQL (Railway/Neon) antes de ejecutar migraciones.
Útil cuando hay conflictos de ENUMs duplicados o schema inconsistente.

USO:
    python clean_railway_db.py [--full-reset]

OPCIONES:
    --full-reset    Elimina TODO el schema public (WARNING: borra todos los datos)
    (sin opciones)  Solo elimina ENUMs existentes (más seguro)

IMPORTANTE:
    - Este script requiere las mismas variables de entorno que la aplicación
    - Asegúrate de tener DATABASE_URL configurado o las variables individuales
    - Usa --full-reset solo si estás seguro de eliminar todos los datos
"""
import asyncio
import sys
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()


# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


async def drop_enums_only(engine):
    """Elimina solo los tipos ENUM existentes sin tocar las tablas."""
    print_info("Eliminando ENUMs existentes...")
    
    enum_types = [
        'estadousuario',
        'estadopedido', 
        'metodopago',
        'tipocupon',
        'estadocupon'
    ]
    
    async with engine.begin() as conn:
        for enum_type in enum_types:
            try:
                await conn.execute(text(f"DROP TYPE IF EXISTS {enum_type} CASCADE;"))
                print_success(f"ENUM '{enum_type}' eliminado")
            except Exception as e:
                print_warning(f"No se pudo eliminar ENUM '{enum_type}': {e}")
    
    print_success("ENUMs eliminados exitosamente")


async def full_reset(engine):
    """Elimina TODO el schema public y lo recrea (DESTRUCTIVO)."""
    print_warning("ADVERTENCIA: Esta operación eliminará TODOS los datos de la base de datos")
    print_warning("Presiona Ctrl+C para cancelar o espera 5 segundos para continuar...")
    
    try:
        await asyncio.sleep(5)
    except KeyboardInterrupt:
        print_info("\nOperación cancelada por el usuario")
        sys.exit(0)
    
    print_info("Eliminando schema public...")
    
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA IF EXISTS public CASCADE;"))
        print_success("Schema public eliminado")
        
        await conn.execute(text("CREATE SCHEMA public;"))
        print_success("Schema public recreado")
        
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO neondb_owner;"))
        print_success("Permisos restaurados")
    
    print_success("Reset completo finalizado")


async def main():
    # Determinar modo de operación
    full_reset_mode = "--full-reset" in sys.argv
    
    # Obtener DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        # Intentar construir desde variables individuales
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "5432")
        db_name = os.getenv("DB_NAME")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        
        if all([db_host, db_name, db_user, db_password]):
            database_url = f"postgresql+asyncpg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
            # Agregar SSL si es un proveedor cloud conocido
            if any(provider in db_host for provider in ["neon.tech", "railway.app", "supabase", "amazonaws"]):
                database_url += "?ssl=require"
        else:
            print_error("ERROR: No se encontró DATABASE_URL ni variables de base de datos")
            print_info("Configura DATABASE_URL o DB_HOST, DB_NAME, DB_USER, DB_PASSWORD")
            sys.exit(1)
    
    # Convertir formato si es necesario
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    print_info(f"Conectando a la base de datos...")
    print_info(f"Host: {database_url.split('@')[1].split('/')[0] if '@' in database_url else 'unknown'}")
    
    # Crear engine
    try:
        engine = create_async_engine(database_url, echo=False)
        
        # Verificar conexión
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version();"))
            version = result.scalar()
            print_success(f"Conectado exitosamente")
            print_info(f"PostgreSQL: {version[:50]}...")
        
        # Ejecutar operación según modo
        if full_reset_mode:
            await full_reset(engine)
        else:
            await drop_enums_only(engine)
        
        await engine.dispose()
        
        print("")
        print_success("Operación completada exitosamente")
        print_info("Ahora puedes ejecutar las migraciones de Alembic:")
        print(f"{Colors.BOLD}  alembic upgrade head{Colors.RESET}")
        
    except Exception as e:
        print_error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    print(f"{Colors.BOLD}=== Limpieza de Base de Datos PostgreSQL (Railway) ==={Colors.RESET}\n")
    asyncio.run(main())
